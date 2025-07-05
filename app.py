import google.generativeai as genai
import os
import json
import re
from flask import Flask, request, jsonify, render_template

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
    1. "incident_number"
    2. "date"
    3. "startTime"
    4. "endTime"
    5. "description" (a concise summary of the request/issue and don't include date, start time, end time and approver)

    Please provide the output in a clean JSON format.

    **Example Input Text:**
    "The file server went down on May 20th, 2024 between 2pm and 3pm. The ticket for this is TCK-58219. It caused a major outage for the entire finance department."

    **Example JSON Output:**
    {{
      "incident_number": "TCK-58219",
      "date": "2024-05-20",
      "startTime": "2pm",
      "endTime": "3pm",
      "description": "The file server went down, causing a major outage for the finance department."
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


# Route to serve the HTML file
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle the data submission from the HTML form
@app.route('/process_data', methods=['POST'])
def process_data():
    if request.is_json:
        data = request.get_json()
        input1 = data.get('input1')
                # --- Your Python Logic Here ---
        # Example: Concatenate the inputs or perform a calculation
        if input1 :
            # output_message = extract_incident_details({input1})
            extracted_data = extract_incident_details({input1})
        else:
            extracted_data = "Please provide input text"
        # --- End of Your Python Logic ---
              
        # --- Approver Extraction and Lookup ---
        # Look for patterns like "approved by [Name/Alias]" or "approver [Name/Alias]"
        approver_alias = "Not found"
        #approver_match = re.search(r'(?:approved by|approver):?\s*([\w\s\.]+)', input1, re.IGNORECASE) # Correct: input_text is used directly
        approver_match = re.search(r'(?:approved by|approver)\s+is\s*([\w\s\.]+)', input1, re.IGNORECASE)
        if approver_match:
            print(f"regext match")
            extracted_alias = approver_match.group(1).strip().lower() # Convert to lowercase for lookup
            print(f"regext match: {extracted_alias}")
            # Attempt to find the exact approver name in our mock DB
            approver = APPROVERS_DB.get(extracted_alias, "Not found in DB")
        else:
            approver = APPROVERS_DB.get("itopslead", "Not found in DB") # If no pattern found in text

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
            print(f"**Approver:** {approver}")
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
            "approver": approver
        }

    # Return the full JSON object
    return jsonify(output_data)

    # Return a JSON response
    return jsonify(output=output_string_for_frontend) # The JS expects 'output' as the key

    #return jsonify(output=extracted_data)
    #return render_template('display.html', data=output_data)
    
if __name__ == '__main__':
    # Ensure the 'templates' folder exists in the same directory as app.py
    # and index.html is inside that 'templates' folder.
    app.run(debug=True) # debug=True allows for automatic reloading on code changes      

