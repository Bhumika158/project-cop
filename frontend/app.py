from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import os
import re
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

# App Configuration
app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'.json', '.postman_collection.json'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# JIRA Config
JIRA_URL= 'https://xxx.atlassian.net'
JIRA_USER= 'xxx@gmail.com'
JIRA_API_TOKEN='xxx'
JIRA_PROJECT_KEY= 'KAN'


# File Extension Check
def allowed_file(filename):
    filename_lower = filename.lower()
    return filename_lower.endswith('.json') or filename_lower.endswith('.postman_collection.json')


# Form Data Validation
def validate_form_data(form_data):
    errors = []

    # Mandatory Fields
    if not form_data.get("project_name"):
        errors.append("Project Name is required.")
    if not form_data.get("description"):
        errors.append("Project Description is required.")
    if not form_data.get("benefits"):
        errors.append("Benefits of the Project are required.")
    if not form_data.get("requestor_name"):
        errors.append("Requestor Name is required.")
    if not form_data.get("requestor_email"):
        errors.append("Requestor Email is required.")
    if not form_data.get("volume_day"):
        errors.append("Volume/day is required.")
    if not form_data.get("payload_size"):
        errors.append("Payload size is required.")
    if not form_data.get("peak_tps"):
        errors.append("Peak TPS is required.")
    if not form_data.get("volume_category"):
        errors.append("Volume Category is required.")
    if not form_data.get("volume_day").isdigit() or not form_data.get("peak_tps").isdigit():
        errors.append("Use Numeric value only.")

    # Proxy Info
    if not form_data.get("BasePath"):
        errors.append("Base Path is required.")
    if not form_data.get("num_api_paths"):
        errors.append("Number of API Paths is required.")
    if form_data.get("num_api_paths") == "Other" and not form_data.get("custom_api_count"):
        errors.append("Specify the number of API paths for 'Other'.")

    # Validate dynamic API Paths
    num_paths = int(form_data.get("custom_api_count") if form_data.get("num_api_paths") == "Other" else form_data.get("num_api_paths"))
    for i in range(1, num_paths + 1):
        if not form_data.get(f"api_path_{i}"):
            errors.append(f"API Path {i} is required.")

    # Source Information
    if not form_data.get("source_app"):
        errors.append("Source App is required.")
    if not form_data.get("vendor_auth_mechanism"):
        errors.append("Vendor Auth Mechanism is required.")
    if form_data.get("vendor_auth_mechanism") != "mTLS+OAuth" and not form_data.get("auth_justification"):
        errors.append("Justification for Auth Mechanism is required.")
    if not form_data.get("pci_data"):
        errors.append("PCI Data information is required.")
    if not form_data.get("data_classification"):
        errors.append("Data classification is required.")
    if not form_data.get("streaming_needed"):
        errors.append("Streaming Needed information is required.")
    if not form_data.get("content_type"):
        errors.append("Request Payload Content-Type is required.")
    if not form_data.get("attachment_document"):
        errors.append("Attachment/Document information is required.")

    # Backend Info
    if not form_data.get("backend_app"):
        errors.append("Backend App is required.")
    if not form_data.get("backend_auth"):
        errors.append("Backend Auth Mechanism is required.")
    if not form_data.get("dev_host"):
        errors.append("Backend DEV Host is required.")
    if not form_data.get("dev_port"):
        errors.append("Backend DEV Port is required.")
    for env in ["dev_host", "sit_host", "uat_host", "prod_host"]:
        value = form_data.get(env)
        if value and not re.match(r"^[a-zA-Z0-9.-]+$", value):  # Host validation
            errors.append(f"Invalid format for {env.replace('_host', '').upper()} HOST. Use valid domain or IP address.")

    for env in ["dev_port", "sit_port", "uat_port", "prod_port"]:
        value = form_data.get(env)
        if value and not re.match(r"^[0-9]+$", value):  # Port validation
            errors.append(f"Invalid format for {env.replace('_port', '').upper()} PORT. Use numeric port only.")

    return errors

# Create Excel Sheet
def create_excel(form_data, file_path):
    try:
        data = {"Field": [], "Value": []}
        for key, value in form_data.items():
            data["Field"].append(key)
            data["Value"].append(value)
        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False)
        print(f"Excel created at: {file_path}")
    except Exception as e:
        print(f"Error creating Excel file: {str(e)}")
        raise

# Submit JIRA Request
def create_jira_ticket(form_data, excel_path, oas_file_path, postman_path):
    try:
        jira_url = f"{JIRA_URL}/rest/api/2/issue"
        auth = HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN)

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        payload = {
            "fields": {
                "project": {"key": JIRA_PROJECT_KEY},
                "summary": form_data['project_name'],
                "description": form_data['description'],
                "issuetype": {"name": "Task"}
            }
        }

        response = requests.post(jira_url, json=payload, headers=headers, auth=auth)
        if response.status_code == 201:
            issue_key = response.json()["key"]

            # Attachments
            attach_file(issue_key, excel_path, auth)
            attach_file(issue_key, oas_file_path, auth)
            attach_file(issue_key, postman_path, auth)
            return issue_key
        else:
            raise Exception(f"Failed to create JIRA ticket: {response.text}")

    except Exception as e:
        print(f"JIRA API Error: {str(e)}")
        raise



def attach_file(issue_key, file_path, auth):
    attachment_url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}/attachments"
    headers = {"X-Atlassian-Token": "no-check"}
    with open(file_path, 'rb') as file:
        files = {"file": file}
        response = requests.post(attachment_url, headers=headers, files=files, auth=auth)
        if response.status_code != 200:
            raise Exception(f"Failed to attach file: {response.text}")

# Routes
@app.route("/", methods=["GET", "POST"])
def form():
    form_data = request.form.to_dict() if request.method == "POST" else {}
    if request.method == "POST":
        errors = validate_form_data(form_data)

        # Handle file uploads
        oas_file = request.files.get("oas_file")
        postman_file = request.files.get("postman_file")

        if not oas_file or oas_file.filename == '':
            errors.append("OAS file is required.")
        elif not allowed_file(oas_file.filename):
            errors.append("Invalid OAS file format.")
        else:
            oas_path = os.path.join(app.config['UPLOAD_FOLDER'], oas_file.filename)
            oas_file.save(oas_path)

        if not postman_file or postman_file.filename == '':
            errors.append("Postman Collection is required.")
        elif not allowed_file(postman_file.filename):
            errors.append("Invalid Postman Collection format.")
        else:
            postman_path = os.path.join(app.config['UPLOAD_FOLDER'], postman_file.filename)
            postman_file.save(postman_path)

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("form.html", data=form_data)

        # Create Excel and JIRA
        excel_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{form_data['project_name']}.xlsx")
        create_excel(form_data, excel_path)

        try:
            jira_key = create_jira_ticket(form_data, excel_path, oas_path, postman_path)
            flash(f"Form submitted successfully! JIRA Ticket: {jira_key}", "success")
        except Exception as e:
            flash(f"Failed to submit JIRA: {str(e)}", "error")
            return render_template("form.html", data=form_data)

        return redirect(url_for("form"))

    return render_template("form.html", data={})

@app.route('/static/sample_oas.yaml')
def download_sample():
    return send_from_directory(directory='static', path='sample_oas.yaml', as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
