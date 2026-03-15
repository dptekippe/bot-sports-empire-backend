"""
Memory HTTP Server
Wraps the vector memory functions for external access
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
sys.path.insert(0, '/Users/danieltekippe/.openclaw/workspace')

from app.core.memory import retrieve, write, health_check

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify(health_check())

@app.route('/retrieve', methods=['POST'])
def retrieve_memory():
    data = request.json
    query = data.get('query', '')
    k = data.get('k', 3)
    results = retrieve(query, k=k)
    return jsonify(results)

@app.route('/write', methods=['POST'])
def write_memory():
    data = request.json
    content = data.get('content', '')
    source = data.get('source', 'api')
    write(content, source)
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
