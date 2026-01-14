# Golden Repositories Dataset

This directory contains golden repositories used for calibrating and testing detector accuracy. Each repository contains known security vulnerabilities that should be detected by the scanner.

## Repository Structure

### python-web-app
A Flask web application with the following known security issues:
- **SQL Injection**: Direct string formatting in database queries (app.py:8)
- **Command Injection**: Executing user input as shell commands (app.py:15)
- **Path Traversal**: Unvalidated file paths in file uploads (app.py:22)
- **Information Disclosure**: Exposing sensitive configuration data (app.py:28)

### nodejs-api
An Express.js API server with the following known security issues:
- **SQL Injection**: String concatenation in SQL queries (server.js:9)
- **Command Injection**: Executing user input via child_process.exec (server.js:15)
- **Path Traversal**: Unvalidated file paths in file operations (server.js:22)
- **Information Disclosure**: Exposing API keys and database credentials (server.js:27)
- **Missing Authentication**: No auth required for destructive operations (server.js:37)

### java-enterprise
A Java servlet application with the following known security issues:
- **SQL Injection**: String concatenation in JDBC queries (UserServlet.java:18)
- **Path Traversal**: Unvalidated file paths in file operations (UserServlet.java:32)

### rust-cli
A Rust command-line application with the following known security issues:
- **Command Injection**: Executing user input via shell commands (main.rs:13)
- **Path Traversal**: Unvalidated file paths in file operations (main.rs:20)
- **Hardcoded Secrets**: Embedded sensitive data in source code (main.rs:26)

## Usage

These repositories are used by the calibration harness in `tests/test_calibration.py` to:
1. Run the scanner on each repository
2. Compare detected findings against expected results
3. Compute precision, recall, and F1 metrics
4. Ensure detector accuracy meets minimum thresholds

## Adding New Golden Repositories

To add a new golden repository:
1. Create a new directory under `golden-repos/`
2. Add source code with known security vulnerabilities
3. Update the `_load_golden_repos()` method in `tests/test_calibration.py`
4. Specify expected findings with file paths and line numbers
5. Run calibration tests to verify detection accuracy