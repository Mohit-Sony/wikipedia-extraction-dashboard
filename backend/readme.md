# Backend Setup Instructions

## Prerequisites
- Python 3.8+ installed
- pip package manager
- Git (for cloning repository)

## 1. Environment Setup

### Create Virtual Environment
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Install Dependencies
```bash
# Install all required packages
pip install -r requirements.txt

# Or install core packages manually (if requirements.txt has issues):
pip install "fastapi[standard]" "uvicorn[standard]" sqlalchemy pandas openpyxl aiohttp beautifulsoup4 lxml pydantic pydantic-settings python-dotenv websockets

# For development (optional):
pip install pytest pytest-asyncio httpx black ruff mypy
```
cd backend && python -m venv fresh_venv && source fresh_venv/bin/activate && pip install fastapi uvicorn sqlalchemy pandas "numpy<2.0" python-multipart websockets aiohttp beautifulsoup4  && python main.py
## 2. Directory Structure Setup

Ensure your backend directory structure matches:
```
backend/
├── main.py
├── requirements.txt
├── database/
│   ├── __init__.py
│   ├── database.py
│   └── models.py
├── api/
│   ├── __init__.py
│   ├── entities.py
│   ├── queues.py
│   ├── analytics.py
│   └── websocket.py
├── services/
│   ├── __init__.py
│   ├── file_service.py
│   ├── sync_service.py
│   ├── extraction_service.py
│   └── deduplication_service.py
└── utils/
    ├── __init__.py
    └── schemas.py
```

## 3. Database Setup

### Create Required Directories
```bash
# Create database directory (if not exists)
mkdir -p ../database

# Create logs directory
mkdir -p ../logs

# Create wikipedia_data directory (for file storage)
mkdir -p ../wikipedia_data
```

### Initialize Database
The database will be automatically created when you first run the application. It uses SQLite by default and will create `../database/entities.db`.

## 4. Environment Configuration (Optional)

Create a `.env` file in the backend directory:
```bash
# backend/.env
DATABASE_URL=sqlite:///../database/entities.db
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
EXTRACTION_DATA_DIR=../wikipedia_data
```

## 5. Start the Backend Server

### Development Mode (Recommended)
```bash
# Make sure you're in the backend directory and virtual environment is active
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the server with auto-reload
python main.py
```

### Alternative: Using Uvicorn Directly
```bash
# Start with uvicorn command
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Mode
```bash
# Start without auto-reload for production
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 6. Verify Installation

### Check Server Status
1. Open browser and go to: `http://localhost:8000`
2. You should see: `{"message": "Wikipedia Extraction Dashboard API", "version": "1.0.0", ...}`

### Check API Documentation
1. Go to: `http://localhost:8000/docs`
2. Interactive API documentation should load (Swagger UI)

### Check Health Endpoint
1. Go to: `http://localhost:8000/health`
2. Should return system health status

### Check WebSocket Connection
1. WebSocket endpoint available at: `ws://localhost:8000/api/v1/ws`

## 7. Common Issues & Troubleshooting

### Import Errors
```bash
# If you get import errors, ensure all __init__.py files exist:
touch database/__init__.py
touch api/__init__.py
touch services/__init__.py
touch utils/__init__.py
```

### Port Already in Use
```bash
# If port 8000 is busy, use a different port:
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Database Permission Issues
```bash
# Ensure database directory has write permissions:
chmod 755 ../database
```

### Missing Dependencies
```bash
# Install specific missing packages:
pip install <package-name>

# Or reinstall all:
pip install -r requirements.txt --force-reinstall
```

## 8. Development Tips

### Auto-reload on Changes
The `--reload` flag automatically restarts the server when you modify Python files.

### View Logs
```bash
# Logs are written to ../logs/dashboard.log
tail -f ../logs/dashboard.log
```

### Database Inspection
```bash
# Install SQLite browser to inspect database:
pip install sqlite-web

# Run SQLite web interface:
sqlite_web ../database/entities.db
```

## 9. API Endpoints Summary

Once running, your API will have these main endpoints:

### Core Endpoints
- `GET /` - API information
- `GET /health` - Health check
- `GET /docs` - API documentation

### Entity Management
- `GET /api/v1/entities` - List entities
- `POST /api/v1/entities/manual` - Add manual entity
- `GET /api/v1/entities/{qid}/preview` - Entity preview

### Queue Management
- `GET /api/v1/queues` - All queues
- `GET /api/v1/queues/{type}` - Specific queue
- `POST /api/v1/queues/entries` - Add to queue

### Extraction Control
- `POST /api/v1/extraction/start` - Start extraction
- `POST /api/v1/extraction/pause` - Pause extraction
- `GET /api/v1/extraction/status` - Extraction status

### Analytics
- `GET /api/v1/analytics/dashboard` - Dashboard stats
- `GET /api/v1/deduplication/stats` - Deduplication stats

### WebSocket
- `WS /api/v1/ws` - Real-time updates

## 10. Next Steps

1. **Start Frontend**: Follow frontend setup instructions
2. **Test Integration**: Ensure frontend can connect to backend
3. **Add Sample Data**: Use the manual entity entry to add test data
4. **Run Extraction**: Test the extraction pipeline

Your backend is now ready! 🚀