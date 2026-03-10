#!/usr/bin/env python3
"""
Agent Shadow - Status Dashboard
Simple HTTP server that displays Agent Shadow status.
"""

import json
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Configuration
PORT = 18787  # Different from OpenClaw's port
BASE_DIR = Path(__file__).parent.parent

def get_status():
    """Get current Agent Shadow status."""
    status = {
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Check queues
    queue_dir = BASE_DIR / "src" / "queue"
    deep_queue_dir = BASE_DIR / "src" / "queue_deep"
    output_dir = BASE_DIR / "src" / "output"
    
    # Fast queue
    if queue_dir.exists():
        fast_pending = len(list(queue_dir.glob("critique_*.json")))
        status["components"]["fast_queue"] = fast_pending
    
    # Deep queue
    if deep_queue_dir.exists():
        deep_pending = len(list(deep_queue_dir.glob("critique_*.json")))
        status["components"]["deep_queue"] = deep_pending
    
    # Output (completed)
    if output_dir.exists():
        completed = len(list(output_dir.glob("*_critique.json")))
        deep_completed = len(list(output_dir.glob("*_deep_critique.json")))
        status["components"]["completed"] = completed + deep_completed
    
    # Config
    config_file = BASE_DIR / "config" / "settings.json"
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
        status["config"] = config
    
    return status

def get_html_status():
    """Generate HTML status page."""
    status = get_status()
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Agent Shadow</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
        }}
        h1 {{
            color: #00d4ff;
            border-bottom: 2px solid #00d4ff;
            padding-bottom: 10px;
        }}
        .card {{
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0;
        }}
        .stat {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .stat:last-child {{ border-bottom: none; }}
        .label {{ color: #aaa; }}
        .value {{ color: #00d4ff; font-weight: bold; }}
        .status-ok {{ color: #4caf50; }}
        .timestamp {{ color: #666; font-size: 0.8em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌓 Agent Shadow</h1>
        
        <div class="card">
            <h3>Status</h3>
            <div class="stat">
                <span class="label">Fast Queue</span>
                <span class="value">{status["components"].get("fast_queue", 0)}</span>
            </div>
            <div class="stat">
                <span class="label">Deep Queue</span>
                <span class="value">{status["components"].get("deep_queue", 0)}</span>
            </div>
            <div class="stat">
                <span class="label">Completed</span>
                <span class="value">{status["components"].get("completed", 0)}</span>
            </div>
        </div>
        
        <div class="card">
            <h3>Configuration</h3>
            <div class="stat">
                <span class="label">Auto-inject</span>
                <span class="value">{status.get("config", {}).get("auto_inject", False)}</span>
            </div>
            <div class="stat">
                <span class="label">Fast Model</span>
                <span class="value">{status.get("config", {}).get("models", {}).get("fast", "qwen3.5:4b")}</span>
            </div>
            <div class="stat">
                <span class="label">Deep Model</span>
                <span class="value">{status.get("config", {}).get("models", {}).get("deep", "qwen3.5:9b")}</span>
            </div>
        </div>
        
        <p class="timestamp">Updated: {status["timestamp"]}</p>
    </div>
</body>
</html>"""
    
    return html

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(get_html_status().encode())
        elif self.path == "/json":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(get_status(), indent=2).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logging

def main():
    print(f"Agent Shadow Dashboard starting on http://localhost:{PORT}")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Dashboard: http://localhost:{PORT}")
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
        server.shutdown()

if __name__ == "__main__":
    main()
