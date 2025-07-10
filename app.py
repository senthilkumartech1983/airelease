import google.generativeai as genai
import os
import json
import re
from flask import Flask, request, jsonify, render_template
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
#from werkzeug.security import generate_password_hash, check_password_hash
import os
import mysql.connector # Import the MySQL connector library
from flask import Flask, request, jsonify, render_template
import os
import streamlit as st

def extract_incident_details(user_text: str):
    """
    Sends user text to the Gemini model to extract incident details.
    """
    # --- Configure the Gemini API Key ---
    # Make sure to set the GOOGLE_API_KEY environment variable.
    try:
        os.environ["GOOGLE_API_KEY"] = "AIzaSyCqSJfni-2eEiFbDl8CpQrXd8Pb_VnrjPc"
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    except KeyError:
        return "Error: GOOGLE_API_KEY environment variable not set."

    # --- Create the Model and Build the Prompt ---
    model = genai.GenerativeModel('gemini-2.5-flash')

    # This detailed prompt with an example helps the model understand the exact format you want.
    prompt = f"""
    **Instruction:**
    From the user-provided text below, extract the following details:
    1. "incident_number" (it can be either one of INC number or RITM request number or JIRA number, priority is INC, then JIRA, then RITM)
    2. "date"
    3. "startTime"
    4. "endTime"
    5. "description" (a concise summary of the request/issue and don't include date, start time, end time and approver)
    6. "approver"

    Current date time is {datetime.now()}

    Please provide the output in a clean JSON format.
     
    **Example Input Text:**
    "The file server went down on May 20th, 2024 between 2pm and 3pm. The ticket for this is TCK-58219. It caused a major outage for the entire finance department. approver is ramesh."

    **Example JSON Output:**
    {{
      "incident_number": "TCK-58219",
      "date": "2024-05-20",
      "startTime": "2pm",
      "endTime": "3pm",
      "description": "The file server went down, causing a major outage for the finance department."
      "approver": "ramesh"
    }}

    ---
    **User-Provided Text to Analyze:**
    "{user_text}"

    **JSON Output:**
    """

    # --- Call the Gemini API ---
    response = model.generate_content(prompt)

    # --- Clean and Parse the Output ---
    try:
        # The model might wrap the JSON in markdown ```json ... ```, so we clean it up.
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned_response)
    except (json.JSONDecodeError, AttributeError):
        return {"error": "Failed to parse the response from the model.", "raw_response": response.text}


app = Flask(__name__)

# --- Mock Database for Approvers ---
# In a real application, this would be a database query.
APPROVERS_DB = {
    "john": "John Doe (Production Lead)",
    "alice": "Alice Smith (Security Manager)",
    "bob": "Robert Johnson (Database Admin)",
    "jane": "Jane C. (Compliance Officer)",
    # Add more mappings as needed
    "itopslead": "IT Operations Lead (Automated Approval)" # Example for a role/alias
}

# Define the UserManager class to handle database interactions for users
class UserManager:
    def __init__(self, db_config):
        self.db_config = db_config

    def _get_db_connection(self):
        """Helper to establish a connection to the MySQL database."""
        try:
            conn = mysql.connector.connect(**self.db_config)
            return conn
        except mysql.connector.Error as err:
            print(f"Error connecting to MySQL: {err}")
            return None

    def _close_db_connection(self, conn, cursor=None):
        """Helper to close database cursor and connection."""
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    def validate_user(self, username, password):
        """
        Validates a user's credentials against the database.
        Returns True if credentials are valid, False otherwise.
        """
        conn = self._get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True) # Get results as dictionaries
            try:
                cursor.execute("SELECT pass FROM users WHERE user_id = %s", (username,))
                user_record = cursor.fetchone()
                print(f"DB result for user '{username}': {user_record}")
                if user_record and user_record['pass'] == password:
                   return user_record
                else:
                   return False
            except mysql.connector.Error as err:
                print(f"Error validating user '{username}': {err}")
                return False
            finally:
                self._close_db_connection(conn, cursor)
        return False # Return False if database connection fails
    
    def getUserCRlist(self, user_id):
        """
        Validates a user's credentials against the database.
        Returns True if credentials are valid, False otherwise.
        """
        print(f"getUserCRlist userid : {user_id}")
        conn = self._get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True) # Get results as dictionaries
            try:
                print(f"before cusrsor userid : {user_id}")
                cursor.execute("SELECT cr_number,cr_ref_number FROM changerequests WHERE cr_userid = %s", (user_id,))
                print(f"after cursor userid : {user_id}")
                crs = cursor.fetchall() # Fetch all rows
                print(f"after fetchall userid : {user_id}")
                # Convert Row objects to dictionaries for JSON serialization
                crs_list = [] # Initialize an empty list
                for row in crs:
                # Each 'row' here is already a dictionary because of dictionary=True
                    crs_list.append(row) 
                print(f"cr list : {crs_list}")
                if crs_list:
                   return crs_list
                else:
                   return False
            except mysql.connector.Error as err:
                   return False
            finally:
                self._close_db_connection(conn, cursor)
        return False # Return False if database connection fails
    
    def checkApproverAvailable(self, approverName):
        """
        Validates a user's credentials against the database.
        Returns True if credentials are valid, False otherwise.
        """
        conn = self._get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True) # Get results as dictionaries
            try:
                print(f"DB result for user '{approverName}': ")
                cursor.execute("SELECT user_id FROM users WHERE fullname LIKE %s", ( approverName,))
                
                result = cursor.fetchone()
                print(f"Raw result from fetchone(): {result}")

                if result:
                    user_id = result['user_id']
                    print(f"Found user_id: {user_id}")
                    return result['user_id']
                else:
                    print("No user found matching the criteria.")
                    return None

                #cursor.execute("SELECT user_id FROM users WHERE fullname LIKE 'ramesh'")
                #user_record = cursor.fetchone()
                #print(f"DB result for user '{approverName}': {user_record}")
                #if user_record:
                #   return user_record
                #else:
                #   return False
            except mysql.connector.Error as err:
                print(f"Error validating user '{approverName}': {err}")
                return False
            finally:
                self._close_db_connection(conn, cursor)
        return False # Return False if database connection fails
    
    def save_changerequests(self, data, userid):
        """
        Validates a user's credentials against the database.
        Returns True if credentials are valid, False otherwise.
        """
        if data.get('incident_number'):
            incnumber = data.get('incident_number')
        else: 
            incnumber = "N/A"
        
        if data.get('date'):
            date = data.get('date')
        else: 
            date = datetime.now().date
        
        if data.get('startTime'):
            startTime = data.get('startTime')
        else: 
            startTime = datetime.now().hour
        
        if data.get('endTime'):
            endTime = data.get('endTime')
        else: 
            endTime = datetime.now().hour+2
        
        if data.get('description'):
            description = data.get('description')
        else: 
            description = "N/A"

        if data.get('approverId'):
            approverId = data.get('approverId')
        else: 
            approverId = "123"    

        conn = self._get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True) # Get results as dictionaries
            try:
                sql_insert_query = """
                                INSERT INTO changerequests (cr_squad_owner,cr_description, cr_ref_number,cr_date, cr_starttime, cr_endtime, cr_approver,cr_creation_date,cr_modify_date,cr_userid)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) """
                record_tuple = ('Beta',description, incnumber, date,startTime, endTime, approverId,datetime.now(),datetime.now(),userid);
                #cursor.execute("INSERT INTO changerequests (cr_description,cr_ref_number,cr_starttime,cr_endtime,cr_approver) = %s %s %s %s %s", ("abcd ",))
                cursor.execute(sql_insert_query, record_tuple)
                conn.commit()
                return True
            except mysql.connector.Error as err:
                print(f"Error while save : {err}")
                return False
            finally:
                self._close_db_connection(conn, cursor)
        return False # Return False if database connection fails

# --- Flask Application Setup ---
app = Flask(__name__)
app.secret_key = os.urandom(24) # Secret key for session management

# --- MySQL Database Configuration ---
# IMPORTANT: Replace these with your actual MySQL database credentials.
# For production, these should be stored securely (e.g., environment variables).
DB_CONFIG = {
    'host': 'localhost', # Or your MySQL server IP/hostname
    'user': 'root', # Your MySQL username
    'password': '365536', # Your MySQL password
    'database': 'changemanagement' # The name of your database
}

# Create an instance of UserManager
user_manager = UserManager(DB_CONFIG)

@app.route('/')
def index():
    """
    The root route. Checks if a user is already logged in.
    If logged in, redirects to the details; otherwise, redirects to the login page.
    """
    if 'username' in session:
        return redirect(url_for('details'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login.
    - GET request: Displays the login form.
    - POST request: Processes the submitted username and password.
    """
    if 'username' in session:
        return redirect(url_for('details'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Use the UserManager to validate credentials
        if user_manager.validate_user(username, password):
            session['username'] = username 
            flash('Login successful!', 'success') 
            return redirect(url_for('details'))
        else:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html', username=username)
    
    return render_template('login.html')

@app.route('/details')
def details():
    """
    The protected details page.
    Only accessible if the user is logged in (i.e., 'username' is in the session).
    """
    if 'username' in session:
        return render_template('details.html', username=session['username'])
    else:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """
    Handles user logout.
    Removes the 'username' from the session, effectively logging the user out.
    """
    session.pop('username', None) 
    flash('You have been logged out.', 'info') 
    return redirect(url_for('login'))

# Route to handle the data submission from the HTML form
@app.route('/process_data', methods=['POST'])
def process_data():
    
    if request.is_json:
        data = request.get_json()
        action = data.get('action')
        print(f"action is : {action}")
        input1 = data.get('input1')
        print(f"input is : {input1}")
                # --- Your Python Logic Here ---
        # Example: Concatenate the inputs or perform a calculation
        if input1 :
            # output_message = extract_incident_details({input1})
            extracted_data = extract_incident_details(input1)
        else:
            extracted_data = "Please provide input text"
        # --- End of Your Python Logic ---
        approverName = extracted_data.get('approver')
        approverUserId = user_manager.checkApproverAvailable(approverName)
        #approverUserId = appData.get('user_id')
        # --- Approver Extraction and Lookup ---
        # Look for patterns like "approved by [Name/Alias]" or "approver [Name/Alias]"
        #approver_alias = "Not found"
        #approver_match = re.search(r'(?:approved by|approver):?\s*([\w\s\.]+)', input1, re.IGNORECASE) # Correct: input_text is used directly
        #approver_match = re.search(r'(?:approved by|approver)\s+is\s*([\w\s\.]+)', input1, re.IGNORECASE)
        #if approver_match:
            #print(f"regext match")
            #extracted_alias = approver_match.group(1).strip().lower() # Convert to lowercase for lookup
            #print(f"regext match: {extracted_alias}")
            # Attempt to find the exact approver name in our mock DB
            # approver = APPROVERS_DB.get(extracted_alias, "Not found in DB")
            #approver = user_manager.checkApproverAvailable(extracted_alias)
        #else:
            #approver = APPROVERS_DB.get("itopslead", "Not found in DB") # If no pattern found in text
            #print("")

        print("\n--- Extracted Details ---")
        if "error" in extracted_data:
            print(f"An error occurred: {extracted_data['error']}")
            print(f"Raw model response: {extracted_data.get('raw_response')}")
        else:
            print(f"**Incident Number:** {extracted_data.get('incident_number', 'Not found')}")
            print(f"**Date:** {extracted_data.get('date', 'Not found')}")
            print(f"**StartTime:** {extracted_data.get('startTime', 'Not found')}")
            print(f"**EndTime:** {extracted_data.get('endTime', 'Not found')}")
            print(f"**Description:** {extracted_data.get('description', 'Not found')}")
            print(f"**Approver:** {extracted_data.get('approver', 'Not found')}")
            print(f"**ApproverId:**", approverUserId)
            
        print("-------------------------\n")
    
    # Format the extracted data into a single string for display in the 'output' div
    # This matches what your JavaScript expects: result.output
    #output_string_for_frontend = (
    #    f"**Incident Number:** {extracted_data.get('incident_number', 'Not found')}\n"
    #    f"**Date:** {extracted_data.get('date', 'Not found')}\n"
    #    f"**Description:** {extracted_data.get('description', 'Not found')}"
    #)
        output_data = {
            "incident_number": extracted_data.get('incident_number', 'Not found'),
            "date": extracted_data.get('date', 'Not found'),
            "startTime": extracted_data.get('startTime', 'Not found'),
            "endTime": extracted_data.get('endTime', 'Not found'),
            "description": extracted_data.get('description', 'Not found'),
            "approverName": extracted_data.get('approver', 'Not found'),
            "approverId": approverUserId,
        }

    # Return the full JSON object
    #return jsonify(output_data)

    # Return a JSON response
    #return jsonify(output=output_string_for_frontend) # The JS expects 'output' as the key
    print("About to call render_template for save.html")
    # Store output_data in the session so save.html can access it
    session['change_data'] = output_data

    # Return a success message (JSON) to the client
    # The client-side JavaScript will then perform the redirect
    return jsonify({"status": "success", "redirect_url": url_for('show_save_page')})
    
    #return jsonify(output=extracted_data)
    #return render_template('display.html', data=output_data)
# A new route to render save.html, which will retrieve data from the session
@app.route('/save_page')
def show_save_page():
    # Retrieve data from the session
    dashboard_data = session.pop('change_data', None) # .pop removes it after use

    if dashboard_data:
        return render_template('save.html', data=dashboard_data)
    else:
        # Handle cases where direct access or session expired
        return redirect(url_for('details')) # Or render an error template

@app.route('/save', methods=['POST'])
def save():
    if request.is_json:
        data = request.get_json()
        incnumber = data.get('incident_number')  
        approverId = data.get('approverId')  
        print(f"INC number passed is : {incnumber}") 
        print(f"approverId is : {approverId}")
        userid =session['username']
        print(f"user id logged in is : {userid}")
        user_manager.save_changerequests(data,userid)
        return True

@app.route('/display_all', methods=['GET'])
def display_all():
    print(f"display all ")
    user_id = session['username']
    print(f"display all :{user_id}")
    crs_list = user_manager.getUserCRlist(user_id)
    print(f"cr all :{crs_list}")

    
    session['crs_list'] = crs_list
    return jsonify({"status": "success", "redirect_url": url_for('display_all_page')})
    

@app.route('/display_all_page')
def display_all_page():
    # Retrieve data from the session
    crs_list_data = session.pop('crs_list', None)

    if crs_list_data:
        return render_template('dashboard.html', data=crs_list_data)
    else:
        # Handle cases where direct access or session expired
        return redirect(url_for('details')) # Or render an error template
    
@app.route('/api/user_change_requests', methods=['GET'])
def get_user_change_requests():
    
    print(f"api all ")
    user_id = session['username']
    print(f"api all :{user_id}")
    crs_list = user_manager.getUserCRlist(user_id)

    # Convert Row objects to dictionaries for JSON serialization
    crs_list = [dict(row) for row in crs_list]
    return jsonify({"status": "success", "change_requests": crs_list})

if __name__ == '__main__':
    # Ensure the 'templates' folder exists in the same directory as app.py
    # and index.html is inside that 'templates' folder.
    app.run(debug=True) # debug=True allows for automatic reloading on code changes      

