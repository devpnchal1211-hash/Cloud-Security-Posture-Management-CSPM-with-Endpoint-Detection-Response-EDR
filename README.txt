
How to Run the Project
Cloud Security Posture Management (CSPM) with Endpoint Detection & Response (EDR)

1. Install Python
First, install Python 3.9 or higher on your system.
Download Python from: https://www.python.org/downloads/

After installation, verify Python using:
python --version


2. Open the Project Folder
Open Command Prompt or Terminal and navigate to the project directory.

Example:
cd cspm-edr-project


3. Install Required Libraries
Install dependencies using requirements.txt:

pip install -r requirements.txt

If requirements.txt is not available, install manually:

pip install flask pandas boto3 reportlab werkzeug python-dotenv


4. Setup the Database
If the project uses SQLite, the database will be created automatically when the app runs.

Example database file:
cspm.db


5. Run the Flask Application
Start the application using:

python app.py

or

flask run


6. Open the Application in Browser
After the server starts you will see:

Running on http://127.0.0.1:5000/

Open this URL in your browser:
http://127.0.0.1:5000


7. Using the Application
After opening the system you can:

- Login or Register
- Start Cloud Security Scan
- Monitor CSPM Results
- View Endpoint Alerts
- Generate Security Reports


Example Workflow

User Login
 ↓
Dashboard
 ↓
Run Cloud Scan
 ↓
CSPM Engine scans cloud configurations
 ↓
EDR monitors endpoint behavior
 ↓
Threat detection
 ↓
Security report generated


Common Errors and Fixes

Error: Flask not installed
pip install flask

Error: Port already in use
flask run --port 8000


Optional: Create Virtual Environment

Create environment:
python -m venv venv

Activate:

Windows:
venv\Scripts\activate

Linux/Mac:
source venv/bin/activate
