# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/auth/login`                                                      | Log in as a teacher                                                 |
| POST   | `/auth/logout`                                                     | Log out                                                             |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only sign up for an activity                                |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only removal from an activity                               |

## Teacher access

Only authenticated teachers can sign up or unregister students. Viewing activities
and participants remains public. Before using teacher mode, create credentials with:

```
python src/create_teacher.py
```

The command securely prompts for a username and password and stores a salted
PBKDF2-HMAC-SHA256 password hash in `src/teachers.json`. That file is ignored by
Git and must be provisioned separately in each environment. Login sessions use an
HTTP-only, same-site cookie; set `COOKIE_SECURE=true` when serving the app over
HTTPS. Set `TEACHER_CREDENTIALS_FILE` to use a credential file outside the source
tree.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
