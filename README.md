Findora is a smart Lost & Found platform designed for college campuses to help students report, search, and recover misplaced belongings easily.
The system connects users who lost items with those who found them through an organized and user-friendly interface.

Directory Structure:

LOST-FOUND/
├── backend/
│   ├── main.py                 # FastAPI app entry point (where CORS goes)
│   ├── database.py             # SQLAlchemy connection setup
│   ├── models.py               # Database tables
│   ├── schemas.py              # Pydantic validation schemas
│   ├── matcher.py              # lost & found matching logic
│   ├── jwt_auth.py             # Token generation & security
│   ├── notifications_service.py # Logic for sending alerts
│   ├── requirements.txt        # Python dependencies
│   ├── lostandfound.db         # SQLite database file
│   ├── .env                    # Secret environment variables
│   ├── router/                 # API endpoint groups
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── items.py
│   │   └── notifications.py
│   └── venv/                   # Python virtual environment
│
└── frontend/
    ├── index.html              # Landing / main page
    ├── dashboard.html          # User dashboard
    ├── login.html              # Login page
    ├── register.html           # Registration page
    ├── report.html             # "Report lost/found item" page
    ├── list.html               # Browsing lost/found items page
    ├── detail.html             # Single item detail view
    ├── layout.html             # (If used for template structure)
    ├── main.css                # Global styles
    ├── home.css                # Landing page specific styles
    └── js/                     # Create a folder for your JS files
        ├── app.js              # Fetch requests to connect to backend
        ├── auth.js             # Handles login/register API calls
        └── items.js            # Handles submitting/fetching items
