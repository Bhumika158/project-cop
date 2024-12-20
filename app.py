from flask import Flask, render_template, request, redirect, url_for, flash
import os
import re  # For regex validation

def validate_form_data(form_data):
    errors = []

    # Validate mandatory fields
    if not form_data.get("project_name"):
        errors.append("Project Name is required.")
    if not form_data.get("description"):
        errors.append("Project Description is required.")
    if not form_data.get("benefits"):
        errors.append("Benefits of the Project are required.")
    if not form_data.get("source"):
        errors.append("Source Information is required.")
    if not form_data.get("source_cn"):
        errors.append("Source Certificate CN info is required.")
    if not form_data.get("dev_info"):
        errors.append("Backend DEV info is required.")
    
    # Validate Backend IP/Host and Port format
    for env in ["dev_info", "sit_info", "uet_info", "prod_info"]:
        value = form_data.get(env)
        if value and not re.match(r"^[a-zA-Z0-9.-]+:[0-9]+$", value):
            errors.append(f"Invalid format for {env.replace('_info', '').upper()} info. Use host:port or IP:port.")
    
    # Validate BPPA Info format
    bppa_info = form_data.get("bppa_info", "")
    if bppa_info and not re.match(r"^([^/]*)(/[^/]*){0,2}$", bppa_info):
        errors.append("Invalid BPPA Info format. Use L4/L3/L2 with '/' separators.")
    
    return errors

app = Flask(__name__)
app.secret_key = "your_secret_key"

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'json', 'yaml'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        # Retrieve form data
        project_name = request.form.get("project_name")
        description = request.form.get("description")
        benefits = request.form.get("benefits")
        pppa_info = request.form.get("pppa_info")
        dev_info = request.form.get("dev_info")
        sit_info = request.form.get("sit_info")
        uet_info = request.form.get("uet_info")
        prod_info = request.form.get("prod_info")
        source = request.form.get("source")
        destination = request.form.get("destination")

        # Validate mandatory fields
        if not project_name or not description or not benefits or not dev_info or not source or not destination:
            flash("Please fill all mandatory fields.", "error")
            return redirect(request.url)

        # Handle file upload
        file = request.files.get("oas_file")
        if not file or not allowed_file(file.filename):
            flash("Please upload a valid OAS specification file.", "error")
            return redirect(request.url)

        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
        flash("Form submitted successfully!", "success")
        return redirect(url_for("form"))

    return render_template("form.html")

if __name__ == "__main__":
    app.run(debug=True)
