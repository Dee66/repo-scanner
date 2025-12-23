
import os
import subprocess

def dangerous_function(user_input):
    # SQL Injection
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    return query

def command_injection(cmd):
    # Command injection vulnerability
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.stdout.decode()

def weak_crypto():
    # Weak encryption
    import hashlib
    return hashlib.md5(b"password").hexdigest()

# Hardcoded secrets
API_KEY = "sk-1234567890abcdef"
DB_PASSWORD = "admin123"
