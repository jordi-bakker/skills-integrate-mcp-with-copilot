"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

logger = logging.getLogger(__name__)
TEACHER_CREDENTIALS_FILE = Path(
    os.environ.get("TEACHER_CREDENTIALS_FILE", current_dir / "teachers.json")
)
PASSWORD_HASH_ITERATIONS = 600_000
SESSION_DURATION_SECONDS = 12 * 60 * 60
SESSION_COOKIE_NAME = "teacher_session"
SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "").lower() == "true"
teacher_sessions: dict[str, tuple[str, float]] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


def _credential_error() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Teacher login is not configured. Follow the setup instructions.",
    )


def _load_teacher_credentials() -> list[dict[str, str]]:
    try:
        data = json.loads(TEACHER_CREDENTIALS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        logger.error("Teacher credentials file is missing: %s", TEACHER_CREDENTIALS_FILE)
        raise _credential_error() from error
    except (OSError, json.JSONDecodeError) as error:
        logger.exception("Unable to read teacher credentials")
        raise HTTPException(
            status_code=500, detail="Teacher credentials are misconfigured."
        ) from error

    if (
        not isinstance(data, dict)
        or not isinstance(data.get("teachers"), list)
        or any(
            not isinstance(teacher, dict)
            or not all(
                isinstance(teacher.get(field), str)
                for field in ("username", "salt", "password_hash")
            )
            for teacher in data["teachers"]
        )
    ):
        logger.error("Teacher credentials file has an invalid structure")
        raise HTTPException(
            status_code=500, detail="Teacher credentials are misconfigured."
        )

    return data["teachers"]


def _password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()


def _get_session_teacher(request: Request) -> str | None:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    session = teacher_sessions.get(session_id) if session_id else None
    if session is None:
        return None

    username, expires_at = session
    if expires_at <= time.time():
        teacher_sessions.pop(session_id, None)
        return None
    return username


def require_teacher(request: Request) -> str:
    username = _get_session_teacher(request)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required")
    return username


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/auth/login")
def login(credentials: LoginRequest, response: Response):
    teacher = next(
        (
            teacher
            for teacher in _load_teacher_credentials()
            if teacher["username"] == credentials.username
        ),
        None,
    )
    salt = teacher["salt"] if teacher is not None else "0" * 32
    expected_hash = teacher["password_hash"] if teacher is not None else "0" * 64
    if not hmac.compare_digest(
        _password_hash(credentials.password, salt), expected_hash
    ) or teacher is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    now = time.time()
    for expired_session_id, (_, expires_at) in list(teacher_sessions.items()):
        if expires_at <= now:
            teacher_sessions.pop(expired_session_id, None)

    session_id = secrets.token_urlsafe(32)
    teacher_sessions[session_id] = (
        credentials.username,
        now + SESSION_DURATION_SECONDS,
    )
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_DURATION_SECONDS,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"message": "Logged in successfully"}


@app.get("/auth/session")
def get_session(request: Request, response: Response):
    username = _get_session_teacher(request)
    response.headers["Cache-Control"] = "no-store"
    return {
        "authenticated": username is not None,
        "username": username,
    }


@app.post("/auth/logout")
def logout(request: Request, response: Response):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        teacher_sessions.pop(session_id, None)
    response.headers["Cache-Control"] = "no-store"
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"message": "Logged out successfully"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str, email: str, _teacher: str = Depends(require_teacher)
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str, email: str, _teacher: str = Depends(require_teacher)
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
