
# Task Manager API

This is a FastAPI application that integrates with Google Calendar and Todoist to help you manage your tasks and events.

## Features

- Create and list Google Calendar events
- Create and list Todoist tasks
- Easy Sync Google Calendar events to Todoist tasks

## Prerequisites

- Python 3.7+
- Google Cloud account with Calendar API enabled
- Todoist account

## Setup

### 1. Clone the repository

```bash
git clone git@github.com:c-i-a-s-t-e-k/easyTaskManager.git
cd easyTaskManager935123
```

### 2. Install dependencies

```bash
pip install fastapi uvicorn httpx google-auth google-api-python-client python-dotenv
```

### 3. Set up Google Calendar API

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Google Calendar API for your project
4. Create a service account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name and description
   - Grant it the "Calendar API" > "Calendar Editor" role
   - Click "Done"
5. Create a key for the service account:
   - Click on the service account you just created
   - Go to the "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Download the key file

### 4. Get your Google Calendar ID

1. Go to [Google Calendar](https://calendar.google.com/)
2. Click on the three dots next to your calendar in the left sidebar
3. Click "Settings and sharing"
4. Scroll down to find your "Calendar ID" (it looks like an email address)
5. Share your calendar with the service account email address (with "Make changes to events" permission)

### 5. Get your Todoist API token

1. Log in to [Todoist](https://todoist.com/)
2. Go to "Settings" > "Integrations" > "Developer"
3. Scroll down to "API token" and copy it

### 6. Create a .env file

Create a `.env` file in the same directory as `taskManager.py` with the following content:

```
GOOGLE_CREDENTIALS_JSON='{"type":"service_account","project_id":"...","private_key_id":"...","private_key":"...","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}'
CALENDAR_ID=your_calendar_id@group.calendar.google.com
TODOIST_TOKEN=your_todoist_api_token
```

For the `GOOGLE_CREDENTIALS_JSON`, copy the entire content of the JSON key file you downloaded and paste it as a single line string.

## Running the application

```bash
uvicorn zad_rest.taskManager:app --reload
```

The application will be available at http://localhost:8000

## API Documentation

Once the application is running, you can access the API documentation at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Web Interface

A simple web interface is available at http://localhost:8000/ where you can:
- Create and list Google Calendar events
- Create and list Todoist tasks
- Sync your Google Calendar events to Todoist tasks

