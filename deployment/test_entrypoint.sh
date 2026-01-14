#!/bin/bash
# Test Entrypoint Script for Rollback Testing
# Simulates various failure scenarios

set -e

# Function to simulate startup failure
simulate_startup_failure() {
    echo "Simulating startup failure..."
    exit 1
}

# Function to simulate runtime failure
simulate_runtime_failure() {
    echo "Starting with runtime failure simulation..."
    sleep 15  # Let initial health checks pass
    echo "Simulating runtime failure..."
    exit 1
}

# Function to simulate health check failure
simulate_health_failure() {
    echo "Starting API server with health check failure..."

    # Start a simple HTTP server that fails health checks
    python3 -c "
import http.server
import socketserver
import time
import sys

class FailingHealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{\"status\": \"unhealthy\"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress log messages

try:
    with socketserver.TCPServer(('', 8080), FailingHealthHandler) as httpd:
        print('Test server running on port 8080 (failing health checks)')
        httpd.serve_forever()
except KeyboardInterrupt:
    pass
"
}

# Check failure scenarios
if [ "$STARTUP_FAILURE" = "true" ]; then
    simulate_startup_failure
elif [ "$RUNTIME_FAILURE" = "true" ]; then
    simulate_runtime_failure
elif [ "$FAILURE_SCENARIO" = "health_check_failure" ]; then
    simulate_health_failure
else
    # Normal operation - start the real API server
    echo "Starting normal API server..."
    exec python -m src.api_server
fi