
from flask import Flask, request
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

@app.route('/user/<username>')
def show_user_profile(username):
    return f'User: {username}'

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    # SECURITY ISSUE: Hardcoded credentials
    if username == 'admin' and password == 'password123':
        return 'Login successful'
    return 'Login failed'

if __name__ == '__main__':
    app.run(debug=True)
