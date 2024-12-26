from flask import Flask, request
import os
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
import git
import shutil
import xml.etree.ElementTree as ET
from lxml import etree
import json

# App Configuration
app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# JIRA Config
JIRA_URL= 'https://xxx.atlassian.net'
JIRA_USER= 'xxx@gmail.com'  
JIRA_API_TOKEN='xxx'
JIRA_PROJECT_KEY= 'KAN'

# GitHub Config
GITHUB_TOKEN = 'xxx'
GITHUB_REPO = f'https://{GITHUB_TOKEN}@github.com/xxx/COPProjectTest.git'
LOCAL_REPO_PATH = 'xxx/COPProjectTest'

# GitHub Config for APIPROXY Repository
GITHUB_PROXY_REPO = f"https://{GITHUB_TOKEN}@github.com/xxx/COPProjectTest_apiproxy.git"
LOCAL_PROXY_REPO_PATH = 'xxx/COPProjectTest_apiproxy'

# Validate Field Criteria
def validate_criteria(data):
    try:
        return (
            float(data.get("payload_size", "0").replace("MB", "").strip()) <= 40 and
            data.get("vendor_auth_mechanism") == "mTLS+OAuth" and
            data.get("pci_data") == "No" and
            data.get("streaming_needed") == "No" and
            data.get("content_type") in ["application/json", "application/xml", "text/plain", "text/xml"] and
            data.get("attachment_document") == "No" and
            data.get("backend_auth") == "mTLS" and 
            int(data.get("volume_day")) <= 100000 and 
            int(data.get("peak_tps")) <= 1000
        )
    except Exception as e:
        print(f"Validation Error: {str(e)}")
        return False

# Fetch JIRA Issue Details
def fetch_jira_issue(issue_key):
    try:
        url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}"
        auth = HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN)
        headers = {"Accept": "application/json"}

        response = requests.get(url, headers=headers, auth=auth)
        if response.status_code == 200:
            issue_data = response.json()
            return issue_data['fields']['attachment']
        else:
            raise Exception(f"Failed to fetch JIRA details: {response.text}")
    except Exception as e:
        print(f"Error fetching JIRA issue: {str(e)}")
        raise

# Read Excel Data from Attachment
def read_excel_from_attachment(file_path):
    try:
        df = pd.read_excel(file_path)
        return dict(zip(df['Field'], df['Value']))
    except Exception as e:
        print(f"Error reading Excel: {str(e)}")
        raise

# Add Comment in JIRA
def add_jira_comment(issue_key, comment):
    try:
        url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}/comment"
        auth = HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN)
        headers = {"Content-Type": "application/json"}
        payload = {"body": comment}

        response = requests.post(url, json=payload, headers=headers, auth=auth)
        if response.status_code != 201:
            raise Exception(f"Failed to add JIRA comment: {response.text}")
    except Exception as e:
        print(f"Error adding comment: {str(e)}")
        raise

# Prettify XML Output
def prettify_xml_lxml(root):
    return etree.tostring(root, pretty_print=True, encoding='utf-8').decode('utf-8')

# GitHub Process
def update_github(issue_key, data):
    try:
        # Clone the repository
        if os.path.exists(LOCAL_REPO_PATH):
            shutil.rmtree(LOCAL_REPO_PATH)
        repo = git.Repo.clone_from(GITHUB_REPO, LOCAL_REPO_PATH, branch='main')

        # Create a new branch
        new_branch = f"{issue_key}"
        repo.git.checkout('-b', new_branch)

        # Update APIValidation.json
        validation_path = os.path.join(LOCAL_REPO_PATH, 'APIValidation.json')
        if os.path.exists(validation_path):
            with open(validation_path, 'r+') as file:
                data_json = json.load(file)
                for i in range(1, int(data.get('num_api_paths', 1)) + 1):
                    new_entry = {
                        "Name": data.get("BasePath", "") + data.get(f"api_path_{i}", ""),
                        "VendorName": data.get("source_app", "")+ ' - '+data.get("backend_app", "")
                    }
                    data_json["API Whitelisting"].append(new_entry)
                file.seek(0)
                json.dump(data_json, file, indent=4)

        # Config.xml and IDPConfig.xml
        for config_file in ['Config.xml', 'IDPConfig.xml']:
            config_path = os.path.join(LOCAL_REPO_PATH, config_file)
            if os.path.exists(config_path):
                parser = etree.XMLParser(remove_blank_text=True)
                tree = etree.parse(config_path, parser)
                root = tree.getroot()

                cert_info = root.find(".//CertificateInfo")
                if cert_info is not None:
                    etree.SubElement(cert_info, 'CN').text = data.get('source_cn_nonprod', '')

                with open(config_path, "wb") as file:
                    file.write(etree.tostring(root, pretty_print=True, encoding='utf-8'))

        # Validate Changes
        repo.git.add(A=True)
        if repo.is_dirty():
            repo.git.commit('-m', f"Updates for JIRA {issue_key}")

        # Push Changes
        repo.git.push('origin', new_branch)

        # Add PR Comment
        add_jira_comment(issue_key, f"Created branch {new_branch} for changes.")

    except Exception as e:
        raise Exception(f"GitHub Process Failed: {str(e)}")
def manage_apiproxy_branch(issue_key, data):
    try:
        # Define the local path for apiproxy repository
        APIPROXY_BRANCH = f"{issue_key}_apiproxy"

        # Clone the repo if it already exists locally, delete it
        if os.path.exists(LOCAL_PROXY_REPO_PATH):
            shutil.rmtree(LOCAL_PROXY_REPO_PATH)

        # Clone repo for apiproxy
        repo = git.Repo.clone_from(GITHUB_PROXY_REPO, LOCAL_PROXY_REPO_PATH, branch='main')

        # Create a new branch for apiproxy
        repo.git.checkout('-b', APIPROXY_BRANCH)

        # Process changes specific to apiproxy
        update_apiproxy(repo, LOCAL_PROXY_REPO_PATH, data)

        # Add and commit changes
        repo.git.add(A=True)
        if repo.is_dirty():
            repo.git.commit('-m', f"APIPROXY Updates for JIRA {issue_key}")

        # Push changes to remote branch
        repo.git.push('origin', APIPROXY_BRANCH)

        # Add JIRA comment
        add_jira_comment(issue_key, f"Created APIPROXY branch {APIPROXY_BRANCH} for changes.")

    except Exception as e:
        raise Exception(f"APIPROXY Process Failed: {str(e)}")


def update_apiproxy(repo, repo_path, data):
    try:
        # Update APIPROXY.xml
        proxy_file = os.path.join(repo_path, 'apiproxy', 'APIPROXY.xml')
        if os.path.exists(proxy_file):
            new_file = os.path.join(repo_path, 'apiproxy', f"{data.get('api_display_name', '')}.xml")
            os.rename(proxy_file, new_file)
            parser = etree.XMLParser(remove_blank_text=True) 
            tree = etree.parse(new_file, parser)
            root = tree.getroot()
            root.set('name', data.get('api_display_name', ''))
            for elem in root.iter('Basepaths'):
                elem.text = data.get('BasePath', '')
            # Write changes with pretty formatting
            with open(new_file, "wb") as file:
                file.write(etree.tostring(root, pretty_print=True, encoding='utf-8'))

        # Update Proxy Endpoint default.xml
        proxy_file = os.path.join(repo_path, 'apiproxy', 'proxies', 'default.xml')
        if os.path.exists(proxy_file):
            tree = ET.parse(proxy_file)
            root = tree.getroot()
            flows = root.find(".//Flows")
            num_paths = int(data.get('num_api_paths', 1))

            # Remove extra flows if paths are fewer
            existing_flows = flows.findall("Flow")
            while len(existing_flows) > num_paths:
                flows.remove(existing_flows.pop())

            # Add or update flows to match paths
            for i in range(num_paths):
                op_name = data.get(f"op_name_{i+1}", f"flow{i+1}")
                if i < len(existing_flows):
                    flow = existing_flows[i]
                    flow.set("name", op_name)
                else:
                    flow = ET.SubElement(flows, 'Flow', name=op_name)
                    ET.SubElement(flow, 'Description')
                    ET.SubElement(flow, 'Request')
                    ET.SubElement(flow, 'Response')
                    ET.SubElement(flow, 'Condition')

                condition = flow.find("Condition")
                condition.text = f'(proxy.pathsuffix MatchesPath "{data.get(f"api_path_{i+1}", "")}") and (request.verb="{data.get(f"request_method_{i+1}", "GET")}")'

            # Update BasePath
            http_connection = root.find(".//HTTPProxyConnection/BasePath")
            if http_connection is not None:
                http_connection.text = data.get("BasePath", "/v1")

            tree.write(proxy_file, xml_declaration=True, encoding='utf-8')

        # Update OAS File
        oas_path = os.path.join(repo_path, 'apiproxy/resources/oas/api.json')
        if os.path.exists(data['oas_file']):
            with open(data['oas_file'], 'r') as infile:
                oas_content = json.load(infile)
            with open(oas_path, 'w') as outfile:
                json.dump(oas_content, outfile, indent=4)

        # Update Target Endpoint default.xml
        target_file = os.path.join(repo_path, 'apiproxy', 'targets', 'default.xml')
        if os.path.exists(target_file):
            tree = ET.parse(target_file)
            root = tree.getroot()
            server = root.find(".//Server")
            if server is not None:
                server.set('name', f"{data.get('api_display_name', '')}-TS")
            tree.write(target_file, xml_declaration=True, encoding='utf-8')

    except Exception as e:
        raise Exception(f"APIPROXY Update Failed: {str(e)}")


# Process JIRA Ticket
@app.route("/process_jira/<issue_key>", methods=["POST"])
def process_jira(issue_key):
    try:
        attachments = fetch_jira_issue(issue_key)
        excel_path = None
        for attachment in attachments:
            if attachment['filename'].endswith('.xlsx'):
                excel_path = os.path.join(UPLOAD_FOLDER, attachment['filename'])
                file_url = attachment['content']
                auth = HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN)
                response = requests.get(file_url, auth=auth)
                with open(excel_path, 'wb') as file:
                    file.write(response.content)
            # Check for OAS file
            elif attachment['filename'] == 'api.json':
                oas_path = os.path.join(UPLOAD_FOLDER, attachment['filename'])
                file_url = attachment['content']
                auth = HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN)
                response = requests.get(file_url, auth=auth)
                with open(oas_path, 'wb') as file:
                    file.write(response.content)

        if not excel_path:
            raise Exception("Excel attachment not found in JIRA ticket.")
        if not oas_path:
            raise Exception("OAS file (api.json) not found in JIRA ticket.")

        data = read_excel_from_attachment(excel_path)
        data['oas_file'] = oas_path

        if validate_criteria(data):
            add_jira_comment(issue_key, "Automatic Execution")
            update_github(issue_key, data)
            manage_apiproxy_branch(issue_key, data)

        else:
            add_jira_comment(issue_key, "Manual Execution")

        return f"Processed JIRA Ticket: {issue_key}", 200
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)
