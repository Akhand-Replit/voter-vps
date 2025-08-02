Akhand Voter VPS: Data Management and Analysis DashboardAkhand Voter VPS is a comprehensive, web-based dashboard designed for managing, analyzing, and visualizing voter and demographic data. Built with Streamlit and backed by a powerful PostgreSQL database, this tool provides an integrated platform for political campaigns, community organizations, or any group needing to work with structured datasets of individuals. The entire interface is in Bengali, making it accessible for local use.✨ Key FeaturesThis application is divided into several modules, each providing a specific set of functionalities:🔒 Secure Authentication: A simple, password-protected login screen to secure access to the dashboard.📊 Interactive Dashboard: A central hub displaying key performance indicators (KPIs) like total records, total batches, and relationship counts (Friends/Enemies).📤 Batch Data Upload: Easily upload voter data from .txt files. Data is organized into batches for better management. The system intelligently parses semi-structured text into a structured database format.✍️ Full Data CRUD Operations:Create: Add new records manually through a dedicated form.Read: View all data in a paginated, editable table.Update: Edit records directly in the "All Data" table or through a specialized "Editable Search" page.Delete: Remove entire batches of data or clear the whole database with confirmation steps.🔍 Advanced Search & Filtering:Perform detailed searches using multiple fields like name, voter number, address, gender, etc.Filter records based on the events they are assigned to.👥 Relationship Management:Categorize individuals into relationships like 'Friend', 'Enemy', or 'Connected'.View dedicated lists for each relationship type.Analyze relationship statistics across different data batches.🗓️ Event Management:Create and manage events (e.g., "Annual Conference 2025").Assign multiple records to one or more events.Filter and view all individuals associated with a specific event.📈 Data Analysis & Visualization:Generate insightful charts and graphs.Analyze data distribution by Gender, Age Group, and Occupation.Filter analytics by specific data batches or view aggregate data.🎂 Age Management: A dedicated page to automatically calculate and update the age of all records based on their date of birth.🖼️ Image Link Generation: An integrated utility to upload an image and generate a direct, shareable link using the ImgBB API.🛠️ Technology StackBackend: Python 3.11Web Framework: StreamlitDatabase: PostgreSQLData Processing: PandasData Visualization: PlotlyContainerization: Docker🚀 Getting StartedFollow these instructions to get a local copy of the project up and running.PrerequisitesPython 3.11 or laterDocker and Docker Compose (Recommended for easiest setup)A running PostgreSQL instance1. Clone the Repositorygit clone [https://github.com/your-username/voter-vps.git](https://github.com/your-username/voter-vps.git)
cd voter-vps
2. Set Up Environment VariablesThe application requires several environment variables to connect to the database and other services. Create a file named .streamlit/secrets.toml and add the following keys:# .streamlit/secrets.toml

# PostgreSQL Database Credentials
DB_HOST = "your_db_host"
DB_PORT = 5432
DB_NAME = "your_db_name"
DB_USER = "your_db_user"
DB_PASSWORD = "your_db_password"

# Application Password
WEB_PASS = "your_secure_login_password"

# ImgBB API Key for Image Uploads
IMGBB_API_KEY = "your_imgbb_api_key"
3. Install DependenciesInstall the required Python packages using the requirements.txt file.pip install -r requirements.txt
4. Run the ApplicationOnce the dependencies are installed and the secrets file is configured, you can run the Streamlit application:streamlit run app.py
The application will be available at http://localhost:8501.🐳 Docker DeploymentFor a more robust and isolated deployment, you can use the provided Dockerfile.1. Build the Docker ImageFrom the root of the project directory, run:docker build -t voter-vps-app .
2. Run the Docker ContainerRun the image as a container, making sure to pass in the environment variables from your secrets.toml file.docker run -p 8813:8813 \
  -e DB_HOST="your_db_host" \
  -e DB_PORT=5432 \
  -e DB_NAME="your_db_name" \
  -e DB_USER="your_db_user" \
  -e DB_PASSWORD="your_db_password" \
  -e WEB_PASS="your_secure_login_password" \
  -e IMGBB_API_KEY="your_imgbb_api_key" \
  --name voter-vps-container \
  voter-vps-app
Note: The Dockerfile exposes port 8813, so we map it to a host port (e.g., 8813).The application will be available at http://localhost:8813.📁 Project Structure.
├── app.py                  # Main Streamlit application file (Dashboard)
├── pages/                  # Contains all other pages of the application
│   ├── 01_Upload.py
│   ├── 02_Search.py
│   └── ...                 # Other application pages
├── utils/
│   ├── database.py         # Handles all PostgreSQL database connections and queries
│   └── styling.py          # Custom CSS and styling for the app
├── attached_assets/
│   ├── auth.py             # Authentication logic
│   └── data_processor.py   # Logic for parsing uploaded text files
├── Dockerfile              # Docker configuration for containerization
├── requirements.txt        # Python package dependencies
└── README.md               # This file
📝 Input Data FormatThe application is designed to parse .txt files containing voter information. Each record should follow this structure, with each piece of information on a new line and a blank line separating each record.Example Format:1. 
নাম: John Doe,
ভোটার নং: 123456789,
পিতা: Richard Doe,
মাতা: Jane Doe,
পেশা: Farmer,
জন্ম তারিখ: 01-01-1980,
ঠিকানা: 123 Main Street, Gazipur,

2. 
নাম: Mary Smith,
ভোটার নং: 987654321,
পিতা: Robert Smith,
মাতা: Susan Smith,
পেশা: Teacher,
জন্ম তারিখ: 05-10-1992,
ঠিকানা: 456 Oak Avenue, Dhaka,
This README was generated to provide a comprehensive overview of the Akhand Voter VPS project.
