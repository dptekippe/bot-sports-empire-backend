# Bot Sports Empire - Optimized for Render Free Tier
FROM python:3.11-slim

WORKDIR /app

# Copy minimal requirements (6 packages, fast install)
COPY requirements-minimal.txt .

# Install Python dependencies (no system deps needed for SQLite)
RUN pip install --no-cache-dir -r requirements-minimal.txt

# Copy application code
COPY . .

# Create data directory for SQLite with write permissions
RUN mkdir -p /app/data && chmod 777 /app/data

# Initialize database (creates empty database with essential tables)
RUN python init_database_simple.py

# Run the application (Render sets $PORT environment variable)
# Add debug output to see startup
CMD ["sh", "-c", "echo '🚀 Starting Bot Sports Empire API on port ${PORT:-10000}' && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]