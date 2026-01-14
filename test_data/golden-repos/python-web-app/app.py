from flask import Flask, request, jsonify
import os
import subprocess

app = Flask(__name__)

@app.route('/api/user/<user_id>')
def get_user(user_id):
    # SQL Injection vulnerability - direct string formatting
    query = f"SELECT * FROM users WHERE id = {user_id}"
    # Execute query (simulated)
    return jsonify({"user": f"User {user_id}"})

@app.route('/api/exec')
def execute_command():
    cmd = request.args.get('cmd')
    # Command injection vulnerability
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return jsonify({"output": result.stdout})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    filename = file.filename
    # Path traversal vulnerability - no validation
    file.save(os.path.join('/tmp/uploads', filename))
    return jsonify({"status": "uploaded"})

@app.route('/api/config')
def get_config():
    # Information disclosure - exposing sensitive config
    return jsonify({
        "database_url": "postgresql://user:password@localhost/db",
        "api_key": "sk-1234567890abcdef",
        "debug": True
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')