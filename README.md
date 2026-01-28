# git-bot-user

A FastAPI application for fetching GitHub users and managing user data with PostgreSQL.

## Prerequisites

1. **PostgreSQL** - Make sure PostgreSQL is installed and running
2. **Python 3.8+** - Python environment
3. **GitHub Token** - For GitHub API access

## Setup Instructions

### 1. Install PostgreSQL

If you don't have PostgreSQL installed:
- **Windows**: Download from [postgresql.org](https://www.postgresql.org/download/windows/)
- **macOS**: `brew install postgresql` or download from postgresql.org
- **Linux**: `sudo apt-get install postgresql` (Ubuntu/Debian) or `sudo yum install postgresql` (CentOS/RHEL)

### 2. Create PostgreSQL Database

Open PostgreSQL command line (`psql`) and run:

```sql
CREATE DATABASE git_users;
```

Or using command line:
```bash
createdb -U postgres git_users
```

### 3. Update Database Credentials (if needed)

If your PostgreSQL credentials differ from the defaults, update these files:
- `app/database.py` - Line 5: `SQLALCHEMY_DATABASE_URL`
- `alembic.ini` - Line 3: `sqlalchemy.url`

Default format: `postgresql://username:password@localhost:5432/git_users`

### 4. Install Python Dependencies

Activate your virtual environment (if using one):
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 5. Set Up Environment Variables

Create a `.env` file in the project root:
```env
# GitHub Token Configuration (choose one):
# Option 1: Single token
GITHUB_TOKEN=your_github_token_here

# Option 2: Multiple tokens (comma-separated) - Recommended for high-volume usage
# The system will automatically rotate between tokens when rate limits are hit
GITHUB_TOKENS=token1,token2,token3,token4

# Location Provider Configuration (choose one)
LOCATION_PROVIDER=nominatim  # Options: nominatim, opencage, google, claude, gemini, groq

# For Geocoding APIs (recommended for location checking):
# OPENCAGE_API_KEY=your_opencage_key  # If using opencage
# GOOGLE_MAPS_API_KEY=your_google_key  # If using google

# For LLM Providers (if using claude, gemini, or groq):
# ANTHROPIC_API_KEY=your_anthropic_key  # If using claude
# GEMINI_API_KEY=your_gemini_key  # If using gemini
# GROQ_API_KEY=your_groq_key  # If using groq
```

**GitHub Token:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate a new token with appropriate permissions
3. Copy the token to your `.env` file

**Multiple Tokens (Recommended):**
- For high-volume API usage, you can provide multiple tokens using `GITHUB_TOKENS`
- Tokens should be comma-separated: `GITHUB_TOKENS=token1,token2,token3`
- The system automatically rotates between tokens when rate limits are encountered
- This significantly reduces rate limiting issues and improves throughput
- If `GITHUB_TOKENS` is set, it takes precedence over `GITHUB_TOKEN`

**Location Provider Options:**

The application supports multiple providers for location checking. Choose one:

1. **Nominatim (FREE, Default)** - OpenStreetMap Nominatim API
   - No API key required
   - Free but rate-limited (1 request/second)
   - Set: `LOCATION_PROVIDER=nominatim`

2. **OpenCage** - OpenCage Geocoding API
   - Get API key: https://opencagedata.com/api
   - Free tier: 2,500 requests/day
   - Set: `LOCATION_PROVIDER=opencage` and `OPENCAGE_API_KEY=your_key`

3. **Google Maps** - Google Maps Geocoding API
   - Get API key: https://console.cloud.google.com/
   - Free tier: $200 credit/month
   - Set: `LOCATION_PROVIDER=google` and `GOOGLE_MAPS_API_KEY=your_key`

4. **Anthropic Claude** - Claude API (LLM)
   - Get API key: https://console.anthropic.com/
   - Set: `LOCATION_PROVIDER=claude` and `ANTHROPIC_API_KEY=your_key`

5. **Google Gemini** - Gemini API (LLM)
   - Get API key: https://makersuite.google.com/app/apikey
   - Set: `LOCATION_PROVIDER=gemini` and `GEMINI_API_KEY=your_key`

6. **Groq** - Groq API (LLM, Fast & Free tier)
   - Get API key: https://console.groq.com/
   - Free tier available
   - Set: `LOCATION_PROVIDER=groq` and `GROQ_API_KEY=your_key`

**Recommendation:** Use **Nominatim** (free) or **OpenCage** (free tier) for location checking as they're more accurate and cost-effective than LLM providers.

### 6. Run Database Migrations

Initialize and run Alembic migrations:
```bash
alembic upgrade head
```

## Running the Application

### Start the FastAPI Server

```bash
uvicorn app.main:app --reload
```

The application will be available at:
- **API**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

### Run the GitHub Users Endpoint

Once the server is running, you can trigger the GitHub users processing:

**Using curl:**
```bash
curl http://localhost:8000/git_users
```

**Using browser:**
Navigate to: http://localhost:8000/git_users

**Using Python:**
```python
import requests
response = requests.get("http://localhost:8000/git_users")
print(response.json())
```

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application entry point
│   ├── database.py      # Database configuration
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   ├── github.py        # GitHub API integration
│   ├── gpt_location.py # Location processing
│   └── mailer.py        # Email functionality
├── alembic/             # Database migrations
├── alembic.ini          # Alembic configuration
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables (create this)
```

## Troubleshooting

### Database Connection Issues

- Ensure PostgreSQL is running: `pg_isready` or check service status
- Verify database exists: `psql -U postgres -l`
- Check credentials in `app/database.py` and `alembic.ini`

### Import Errors

- Make sure you're in the project root directory
- Activate your virtual environment
- Install all dependencies: `pip install -r requirements.txt`

### GitHub API Rate Limits

The application handles rate limits automatically, but if you encounter issues:
- Check your GitHub token is valid
- Ensure the token has appropriate permissions
- Wait for rate limit reset (shown in console output)

## Development

To run in development mode with auto-reload:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```