# 📋 LEAGUE CREATION API - COMPLETE TECHNICAL SPECIFICATIONS

## 🏈 **Date:** 2026-02-13 07:33 CST
## 🤖 **By:** Roger the Robot (following Nova's recommendation)
## 🎯 **Purpose:** Provide detailed specs for Minimax to generate drop-in ready code

---

## 1. BACKEND TECH STACK CONFIRMATION

### **Current Backend Framework:**
- **✅ FastAPI** (confirmed from `main.py`)
- **Version:** Python 3.11.0 (Render deployment)
- **Location:** `/Users/danieltekippe/.openclaw/workspace/bot-sports-empire/main.py`

### **Database:**
- **Current:** In-memory dictionaries (NO DATABASE YET)
- **Planned:** **PostgreSQL** (based on Daniel's profile)
- **Current storage:** JSON files (`waitlist.json`)
- **ORM:** **SQLAlchemy** (planned, not yet implemented)

### **Project Structure:**
```
bot-sports-empire/
├── main.py              # Entry point (FastAPI app)
├── requirements.txt     # Dependencies
├── render.yaml         # Render deployment config
├── waitlist.json       # Current data storage
└── (static files served from parent directory)
```

### **Current API Routes (from `main.py`):**
- `GET /` - Landing page
- `GET /register` - Registration instructions  
- `GET /login` - Login placeholder
- `GET /health` - Health check
- `POST /api/waitlist` - Waitlist signup
- `GET /api/waitlist/{email}` - Check waitlist status

---

## 2. AUTHENTICATION INTEGRATION

### **Current Authentication:**
- **Frontend:** Demo API keys in `login.html` (`key_roger_bot_123`, `key_test_bot_456`)
- **Storage:** `sessionStorage` in browser
- **Backend:** **NO AUTHENTICATION YET** - endpoints don't validate API keys

### **Authentication Function Needed:**
```python
# NEED TO BE CREATED:
async def verify_api_key(api_key: str) -> Optional[Dict]:
    """
    Verify API key and return bot info.
    Currently simulated in frontend, needs real implementation.
    """
    # Should query database for bot with this API key
    # Return bot info: {id, name, x_handle, etc.}
    pass
```

### **Bot Storage Concept:**
```python
# Current frontend simulation (login.html):
validApiKeys = {
    'key_roger_bot_123': {
        'botName': 'Roger the Robot',
        'botId': 'roger_bot_123',
        'xHandle': '@Roger2_Robot',
        'leagues': []
    }
}
```

---

## 3. DATABASE SCHEMA DESIGN

### **League Model Specification:**
```python
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class League(Base):
    __tablename__ = "leagues"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Required Fields (from frontend)
    name = Column(String(50), nullable=False)  # Max 50 chars (frontend validation)
    format = Column(String(20), nullable=False)  # "dynasty" or "fantasy"
    attribute = Column(String(50), nullable=False)  # One of 5 personality types
    
    # Relationships
    creator_bot_id = Column(String(50), nullable=False)  # Links to bot ID
    
    # Status & Metadata
    status = Column(String(20), default="forming")  # "forming", "active", "draft", "completed"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # League Settings (simplified for MVP)
    team_count = Column(Integer, default=12)  # Fixed at 12 teams
    visibility = Column(String(20), default="public")  # "public" or "private"
    max_leagues_per_bot = Column(Integer, default=3)  # Enforcement limit
```

### **Bot Model (for reference):**
```python
class Bot(Base):
    __tablename__ = "bots"
    
    id = Column(String(50), primary_key=True)  # e.g., "roger_bot_123"
    name = Column(String(100), nullable=False)
    display_name = Column(String(100))
    description = Column(Text)
    x_handle = Column(String(100))  # Twitter/X handle
    api_key = Column(String(100), unique=True, nullable=False)  # Hashed
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    leagues = relationship("League", backref="creator")
```

---

## 4. API ENDPOINT SPECIFICATION

### **Endpoint:** `POST /api/v1/leagues`
**Purpose:** Create a new league with personality-based attributes

#### **Headers:**
```
Authorization: Bearer <api_key>
# OR (simpler for MVP):
X-API-Key: <api_key>
Content-Type: application/json
```

#### **Request Body:**
```json
{
  "name": "AI Dynasty Champions",
  "format": "dynasty",
  "attribute": "stat_nerds"
}
```

#### **Field Validation:**
- `name`: string, 3-50 characters, required
- `format`: enum, must be "dynasty" or "fantasy", required
- `attribute`: enum, must be one of:
  - "stat_nerds" (📊 Stat Nerds League)
  - "trash_talk" (🗣️ Trash Talk Titans)  
  - "dynasty_purists" (👑 Dynasty Purists)
  - "redraft_revolutionaries" (🔄 Redraft Revolutionaries)
  - "casual_competitors" (☕ Casual Competitors)

#### **Success Response (201 Created):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "AI Dynasty Champions",
  "format": "dynasty",
  "attribute": "stat_nerds",
  "creator_bot_id": "roger_bot_123",
  "creator_bot_name": "Roger the Robot",
  "status": "forming",
  "team_count": 12,
  "visibility": "public",
  "created_at": "2026-02-13T07:30:00Z",
  "message": "League created successfully. Waiting for 11 more bots to join."
}
```

#### **Error Responses:**
- `400 Bad Request` - Invalid input (validation failed)
- `401 Unauthorized` - Invalid or missing API key
- `409 Conflict` - League name already exists (unique constraint)
- `422 Unprocessable Entity` - Pydantic validation error
- `500 Internal Server Error` - Server error

---

## 5. INTEGRATION POINTS

### **File Locations:**
1. **Main Application:** `bot-sports-empire/main.py` (add new routes here for MVP)
2. **Future Structure:** Create `bot-sports-empire/routes/leagues.py`
3. **Models:** Create `bot-sports-empire/models.py`
4. **Database:** Create `bot-sports-empire/database.py`

### **Dependencies (from current `requirements.txt`):**
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
email-validator==2.1.0
```

### **Additional Dependencies Needed:**
```txt
sqlalchemy==2.0.23
alembic==1.13.1
psycopg2-binary==2.9.9  # For PostgreSQL
python-multipart==0.0.6
```

### **Authentication Middleware:**
Need to create simple API key validation:
```python
# In main.py or auth.py
async def get_current_bot(api_key: str = Header(..., alias="X-API-Key")):
    bot = await verify_api_key(api_key)
    if not bot:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return bot
```

### **Database Migrations:**
- Use **Alembic** for schema changes
- Initial migration: Create `leagues` and `bots` tables
- Migration location: `bot-sports-empire/alembic/`

---

## 6. FRONTEND INTEGRATION SPECIFICS

### **Current Frontend Expectation:**
From `dashboard.html` line ~1050:
```javascript
// Simulated API call (REPLACE THIS)
setTimeout(() => {
    // Show success message
    modalStatus.className = 'status-message status-success';
    modalStatus.innerHTML = `✅ League Created Successfully!`;
    // ... rest of UI updates
}, 1200); // Simulate API delay
```

### **Required Frontend Changes:**
```javascript
// REPLACE WITH REAL API CALL
fetch('/api/v1/leagues', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': sessionStorage.getItem('apiKey')
    },
    body: JSON.stringify({
        name: leagueName,
        format: selectedFormat,
        attribute: selectedAttribute
    })
})
.then(response => response.json())
.then(data => {
    // Show success with real data
    modalStatus.className = 'status-message status-success';
    modalStatus.innerHTML = `
        <strong>✅ ${data.message}</strong><br>
        <span style="font-size: 0.9rem;">
            "${data.name}" is now ${data.status}.<br>
            Format: ${data.format} | Style: ${data.attribute}
        </span>
    `;
    // Update dashboard windows with real league data
    addLeagueToDashboard(data);
})
.catch(error => {
    // Show error message
    modalStatus.className = 'status-message status-error';
    modalStatus.innerHTML = `❌ Error: ${error.message}`;
});
```

---

## 7. MVP IMPLEMENTATION PRIORITY

### **Phase 1 (Today):**
1. **SQLite database** (simpler than PostgreSQL for MVP)
2. **Basic API key validation** (in-memory or simple DB)
3. **League creation endpoint** with SQLAlchemy
4. **Frontend integration** (replace simulated API call)

### **Phase 2 (Later):**
1. **PostgreSQL migration**
2. **Full authentication system**
3. **Alembic migrations**
4. **Join league functionality**
5. **Draft system**

---

## 🎯 READY FOR MINIMAX

**Now Minimax has complete specifications to generate:**
1. ✅ Database models matching our schema design
2. ✅ API endpoints with proper validation
3. ✅ Authentication integration
4. ✅ Error handling matching our patterns
5. ✅ Frontend integration code

**No assumptions needed - everything is documented!**