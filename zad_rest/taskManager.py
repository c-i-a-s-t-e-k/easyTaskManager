from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Optional
import httpx
import os
from pydantic import BaseModel
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

app = FastAPI(
    title="Task Manager API",
    description="API for integrating with Google Calendar and Todoist",
    version="0.1.0",
)

# Mount static files directory if it exists
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Serve the index.html page at the root URL
@app.get("/", response_class=HTMLResponse)
async def get_index():
    html_file = Path(__file__).parent / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(), status_code=200)
    else:
        raise HTTPException(status_code=404, detail="Index page not found")

# --- Models ---

class CalendarEvent(BaseModel):
    summary: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None

class TodoistTask(BaseModel):
    content: str
    description: Optional[str] = None 
    due_date: Optional[datetime] = None
    priority: Optional[int] = 1  # 1-4, 4 being highest

# --- Authentication ---

async def get_google_calendar_service():
    try:
        # Load credentials from environment variable or file
        if GOOGLE_CREDENTIALS_JSON:
            # If credentials are stored as a JSON string in env var
            credentials_info = json.loads(GOOGLE_CREDENTIALS_JSON)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info, 
                scopes=['https://www.googleapis.com/auth/calendar']
            )
        else:
            raise FileNotFoundError("Google credentials file not found")
        
        # Build the service
        service = build('calendar', 'v3', credentials=credentials)
        return service
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize Google Calendar service: {str(e)}"
        )


load_dotenv(Path(__file__).parent / ".env")

GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
GOOGLE_CALENDAR_ID = os.environ.get("CALENDAR_ID")
TODOIST_TOKEN = os.environ.get("TODOIST_TOKEN")

async def get_todoist_client():
    return httpx.AsyncClient(
        base_url="https://api.todoist.com/rest/v2/",
        headers={"Authorization": f"Bearer {TODOIST_TOKEN}"}
    )


# --- Google Calendar Endpoints ---

@app.post("/calendar/events/", response_model=CalendarEvent)
async def create_calendar_event(
    summary: str = Form(...),
    description: Optional[str] = Form(None),
    start_time: str = Form(...),
    end_time: str = Form(...),
    location: Optional[str] = Form(None)
):
    try:
        # Convert string times to datetime objects
        start_time_dt = datetime.fromisoformat(start_time)
        end_time_dt = datetime.fromisoformat(end_time)
        
        
        service = await get_google_calendar_service()
        
        event_data = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_time_dt.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time_dt.isoformat(),
                "timeZone": "UTC",
            },
        }
        
        if location:
            event_data["location"] = location
        
        created_event = service.events().insert(
            calendarId=GOOGLE_CALENDAR_ID,
            body=event_data
        ).execute()
        
        # Parse the response to match our model
        start_time = datetime.fromisoformat(created_event["start"]["dateTime"].replace("Z", ""))
        end_time = datetime.fromisoformat(created_event["end"]["dateTime"].replace("Z", ""))
        
        return CalendarEvent(summary, description, start_time, end_time, location)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create calendar event: {str(e)}"
        )

@app.get("/calendar/events/", response_class=HTMLResponse)
async def list_calendar_events(
    max_results: int = 10,
    time_min: Optional[datetime] = None
):
    try:
        service = await get_google_calendar_service()
        
        # Prepare parameters
        params = {
            "maxResults": max_results,
            "calendarId": GOOGLE_CALENDAR_ID or "primary",
            "singleEvents": True,
            "orderBy": "startTime"
        }
        
        if time_min:
            params["timeMin"] = time_min.isoformat() + "Z"
        else:
            # Default to events from now onwards
            params["timeMin"] = datetime.now().isoformat() + "Z"
        
        # Execute the API call
        events_result = service.events().list(**params).execute()
        events_data = events_result.get("items", [])
        
        events = []
        for event_data in events_data:
            # Handle different date formats (dateTime vs date)
            start = event_data["start"].get("dateTime", event_data["start"].get("date"))
            end = event_data["end"].get("dateTime", event_data["end"].get("date"))
            
            # Parse the datetime strings
            if "T" in start:  # It's a dateTime format
                start_time = datetime.fromisoformat(start.replace("Z", ""))
                end_time = datetime.fromisoformat(end.replace("Z", ""))
            else:  # It's a date format
                start_time = datetime.strptime(start, "%Y-%m-%d")
                end_time = datetime.strptime(end, "%Y-%m-%d")
            
            event = CalendarEvent(
                summary=event_data.get("summary", ""),
                description=event_data.get("description", ""),
                start_time=start_time,
                end_time=end_time,
                location=event_data.get("location", "")
            )
            events.append(event)
        
        return events
        
    except Exception as e:  
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving calendar events: {str(e)}"
        )

# --- Todoist Endpoints ---
@app.post("/todoist/tasks/", response_class=HTMLResponse)
async def create_todoist_task(
    content: str = Form(...),
    description: Optional[str] = Form(None),
    due_date: Optional[str] = Form(None),
    priority: int = Form(1),
    client: httpx.AsyncClient = Depends(get_todoist_client)
):
    try:
        task_data = {
            "content": content,
        }
        
        if description:
            task_data["description"] = description
        
        if due_date and due_date.strip():
            # Convert string date to datetime
            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
            task_data["due_date"] = due_date_obj.strftime("%Y-%m-%d")
        
        if priority:
            task_data["priority"] = priority
        
        response = await client.post("tasks", json=task_data)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create Todoist task"
            )
        
         
        return TodoistTask(content, description, due_date, priority)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create Todoist task: {str(e)}"
        )

@app.get("/todoist/tasks/", response_class=HTMLResponse)
async def list_todoist_tasks(
    client: httpx.AsyncClient = Depends(get_todoist_client)
):
    try:
        response = await client.get("tasks")
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve Todoist tasks"
            )
        
        tasks_data = response.json()
        tasks = []
        
        for task_data in tasks_data:
            due = None
            due_str = None
            if "due" in task_data and task_data["due"]:
                due_str = task_data["due"].get("date")
                if due_str:
                    due = datetime.strptime(due_str, "%Y-%m-%d")
            
            task = TodoistTask(
                content=task_data["content"],
                description=task_data.get("description", ""),
                due_date=due,
                priority=task_data.get("priority", 1)
            )
            tasks.append(task)
        
        return tasks
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve Todoist tasks: {str(e)}"
        )

# --- Integration Endpoint ---


@app.post("/sync-calendar-to-todoist/", response_class=HTMLResponse)
async def sync_calendar_to_todoist(
    todoist_client: httpx.AsyncClient = Depends(get_todoist_client),
    days_ahead: int = 7
):
    try:
        service = await get_google_calendar_service()
        
        # Get upcoming events
        time_min = datetime.now()
        time_max = time_min + timedelta(days=days_ahead)
        
        # Prepare parameters
        params = {
            "timeMin": time_min.isoformat() + "Z",
            "timeMax": time_max.isoformat() + "Z",
            "singleEvents": True,
            "orderBy": "startTime",
            "calendarId": GOOGLE_CALENDAR_ID
        }
        
        # Execute the API call
        events_result = service.events().list(**params).execute()
        events_data = events_result.get("items", [])
        
        created_tasks = []
        
        for event_data in events_data:
            # Create a task for each event
            task_data = {
                "content": f"Calendar: {event_data.get('summary', 'Event')}",
                "description": event_data.get("description", ""),
            }
            
            # Set due date to event start time
            if "start" in event_data and "dateTime" in event_data["start"]:
                start_time = datetime.fromisoformat(event_data["start"]["dateTime"].replace("Z", ""))
                task_data["due_date"] = start_time.strftime("%Y-%m-%d")
                task_data["due_datetime"] = event_data["start"]["dateTime"]
            
            task_response = await todoist_client.post("tasks", json=task_data)
            
            if task_response.status_code == 200:
                task_json = task_response.json()
                
                # Convert the JSON response to a TodoistTask object
                due_date = None
                if "due" in task_json and task_json["due"]:
                    due_str = task_json["due"].get("date")
                    if due_str:
                        due_date = datetime.strptime(due_str, "%Y-%m-%d")
                
                task = TodoistTask(
                    content=task_json["content"],
                    description=task_json.get("description", ""),
                    due_date=due_date,
                    priority=task_json.get("priority", 1)
                )
                created_tasks.append(task)
        
        return created_tasks
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync calendar to Todoist: {str(e)}"
        )