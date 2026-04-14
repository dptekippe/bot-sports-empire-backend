"""
Memory HTTP Server - Enhanced
Wraps the vector memory functions for external access
Enhanced with: logging, error handling, timeouts, graceful shutdown, connection pooling
"""
import logging
import os
import signal
import sys
import threading
import atexit
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.serving import make_server
import psycopg2
from psycopg2 import pool

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('memory_server')

# Add request ID for tracing
import uuid
from functools import wraps

def setup_request_context(f):
    """Decorator to add request ID to each request"""
    @wraps(f)
    def decorated(*args, **kwargs):
        request_id = str(uuid.uuid4())[:8]
        logger.info(f"[{request_id}] {request.method} {request.path}")
        try:
            result = f(*args, **kwargs)
            logger.info(f"[{request_id}] Success")
            return result
        except Exception as e:
            logger.error(f"[{request_id}] Error: {e}")
            raise
    return decorated

# Import memory functions AFTER logging setup
sys.path.insert(0, '/Users/danieltekippe/.openclaw/workspace')
from app.core.memory import retrieve, write, health_check

app = Flask(__name__)
CORS(app)

# Configuration
HOST = '127.0.0.1'
PORT = int(os.getenv('MEMORY_SERVER_PORT', 5001))
REQUEST_TIMEOUT = 30  # seconds

# Graceful shutdown state
shutdown_event = threading.Event()
server = None

class TimeoutError(Exception):
    pass

def run_with_timeout(func, timeout_seconds):
    """Execute a function with a timeout"""
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError:
            logger.warning(f"Operation timed out after {timeout_seconds}s")
            raise TimeoutError(f"Operation exceeded {timeout_seconds}s timeout")

def log_db_error(operation, error):
    """Structured DB error logging"""
    logger.error(f"DB error during {operation}: {type(error).__name__}: {error}")

@app.route('/health', methods=['GET'])
@setup_request_context
def health():
    """
    Health check endpoint
    Returns: {"status": "ok", "memories": count} or {"status": "error", "message": "..."}
    """
    try:
        result = health_check()
        return jsonify(result)
    except Exception as e:
        log_db_error("health_check", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/retrieve', methods=['POST'])
@setup_request_context
def retrieve_memory():
    """
    Semantic memory retrieval endpoint
    Body: {"query": "search text", "k": 3}
    Returns: [{"content": "...", "type": "...", "importance": ..., ...}]
    """
    try:
        data = request.get_json() or {}
        
        # Input validation
        query = data.get('query', '')
        if not query:
            return jsonify({"error": "query is required"}), 400
        
        k = data.get('k', 3)
        if not isinstance(k, int) or k < 1 or k > 100:
            return jsonify({"error": "k must be integer between 1 and 100"}), 400
        
        # Execute with timeout
        def _retrieve():
            return retrieve(query, k=k)
        
        results = run_with_timeout(_retrieve, REQUEST_TIMEOUT)
        return jsonify(results)
        
    except TimeoutError:
        logger.error("Retrieve operation timed out")
        return jsonify({"error": "Request timed out"}), 504
    except Exception as e:
        log_db_error("retrieve", e)
        return jsonify({"error": str(e)}), 500

@app.route('/write', methods=['POST'])
@setup_request_context
def write_memory():
    """
    Memory write endpoint
    Body: {"content": "memory text", "source": "api", ...}
    Returns: {"status": "ok", "memory_count": count}
    """
    try:
        data = request.get_json() or {}
        
        # Input validation
        content = data.get('content', '')
        if not content:
            return jsonify({"error": "content is required"}), 400
        
        if len(content) > 50000:
            return jsonify({"error": "content exceeds 50KB limit"}), 400
        
        source = data.get('source', 'api')
        
        # Execute with timeout
        def _write():
            write(content, source)
            # Get updated count
            with psycopg2.connect(os.getenv(
                "DATABASE_URL",
                "postgresql://dynastydroid_user:***@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
            )) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM memories")
                    return cur.fetchone()[0]
        
        count = run_with_timeout(_write, REQUEST_TIMEOUT)
        logger.info(f"Memory written. Total memories: {count}")
        return jsonify({"status": "ok", "memory_count": count})
        
    except TimeoutError:
        logger.error("Write operation timed out")
        return jsonify({"error": "Request timed out"}), 504
    except Exception as e:
        log_db_error("write", e)
        return jsonify({"error": str(e)}), 500

@app.route('/stats', methods=['GET'])
@setup_request_context
def stats():
    """Memory statistics endpoint"""
    try:
        result = health_check()
        return jsonify({
            "total_memories": result.get("memories", 0),
            "status": result.get("status", "unknown")
        })
    except Exception as e:
        log_db_error("stats", e)
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500

def graceful_shutdown(signum=None, frame=None):
    """Graceful shutdown handler"""
    logger.info("Received shutdown signal, stopping server...")
    shutdown_event.set()
    if server:
        logger.info("Shutting down Flask server...")
        server.shutdown()
    logger.info("Server stopped gracefully")

def register_shutdown_handlers():
    """Register signal handlers for graceful shutdown"""
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, graceful_shutdown)
    if hasattr(signal, 'SIGINT'):
        signal.signal(signal.SIGINT, graceful_shutdown)
    
    # Also register with atexit
    atexit.register(lambda: logger.info("Server shutdown complete"))

if __name__ == '__main__':
    import os
    
    logger.info(f"Starting Memory Server on {HOST}:{PORT}")
    logger.info(f"Request timeout: {REQUEST_TIMEOUT}s")
    
    # Register shutdown handlers
    register_shutdown_handlers()
    
    try:
        server = make_server(HOST, PORT, app, threaded=True)
        logger.info(f"Memory Server ready - PID: {os.getpid()}")
        
        # Serve until shutdown
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        graceful_shutdown()
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
