"""Real-time dashboard for metrics visualization."""

import os
from typing import Dict, Any
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import time

# Optional dashboard imports
try:
    from .metrics_collector import get_metrics_collector
    from .alerting import get_alert_manager
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False

# HTML template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Repository Scanner - Real-time Dashboard</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .metric-title {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #666;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        .metric-unit {
            font-size: 0.8em;
            color: #666;
        }
        .status-good { color: #22c55e; }
        .status-warning { color: #f59e0b; }
        .status-error { color: #ef4444; }
        .alerts-section {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .alert-item {
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 4px solid;
        }
        .alert-high { border-left-color: #ef4444; background: #fef2f2; }
        .alert-medium { border-left-color: #f59e0b; background: #fffbeb; }
        .alert-low { border-left-color: #22c55e; background: #f0fdf4; }
        .logs-section {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-top: 20px;
        }
        .log-item {
            padding: 8px;
            margin: 2px 0;
            border-radius: 3px;
            font-family: monospace;
            font-size: 0.85em;
            border-left: 3px solid;
        }
        .log-INFO { border-left-color: #3b82f6; background: #eff6ff; }
        .log-WARNING { border-left-color: #f59e0b; background: #fffbeb; }
        .log-ERROR { border-left-color: #ef4444; background: #fef2f2; }
        .log-DEBUG { border-left-color: #6b7280; background: #f9fafb; }
        .log-controls {
            margin-bottom: 15px;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .log-controls input, .log-controls select {
            padding: 5px;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
        .log-controls button {
            padding: 5px 10px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }
        .log-controls button:hover {
            background: #5a67d8;
        }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1em;
        }
        .refresh-btn:hover {
            background: #5a67d8;
        }
        .last-updated {
            text-align: center;
            color: #666;
            font-size: 0.9em;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Repository Intelligence Scanner</h1>
        <p>Real-time Monitoring Dashboard</p>
    </div>

    <div class="metrics-grid" id="metrics-grid">
        <!-- Metrics will be loaded here -->
    </div>

    <div class="alerts-section">
        <h2>🚨 Active Alerts</h2>
        <div id="alerts-list">
            <!-- Alerts will be loaded here -->
        </div>
    </div>

    <div class="logs-section">
        <h2>📋 Recent Logs</h2>
        <div class="log-controls">
            <select id="log-filter">
                <option value="recent">Recent Logs</option>
                <option value="errors">Errors Only</option>
                <option value="warnings">Warnings Only</option>
                <option value="api">API Server Logs</option>
            </select>
            <input type="text" id="log-search" placeholder="Search logs..." style="flex: 1;">
            <button onclick="filterLogs()">Filter</button>
            <button onclick="refreshLogs()">Refresh Logs</button>
        </div>
        <div id="logs-list" style="max-height: 400px; overflow-y: auto;">
            <!-- Logs will be loaded here -->
        </div>
    </div>

    <div class="last-updated" id="last-updated">
        Loading...
    </div>

    <script>
        let metricsData = {};
        let alertsData = [];
        let logsData = [];

        async function fetchData() {
            try {
                const [metricsResponse, alertsResponse, logsResponse] = await Promise.all([
                    fetch('/api/dashboard/metrics'),
                    fetch('/api/dashboard/alerts'),
                    fetch('/api/logs/recent?limit=50')
                ]);

                metricsData = await metricsResponse.json();
                alertsData = await alertsResponse.json();
                logsData = await logsResponse.json();

                updateDashboard();
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }

        async function refreshLogs() {
            try {
                const logsResponse = await fetch('/api/logs/recent?limit=50');
                logsData = await logsResponse.json();
                updateLogs();
            } catch (error) {
                console.error('Error fetching logs:', error);
            }
        }

        function filterLogs() {
            const filter = document.getElementById('log-filter').value;
            const search = document.getElementById('log-search').value.toLowerCase();
            updateLogs(filter, search);
        }

        function updateDashboard() {
            updateMetrics();
            updateAlerts();
            updateLogs();
            updateTimestamp();
        }

        function updateMetrics() {
            const grid = document.getElementById('metrics-grid');

            // HTTP metrics
            const httpCounters = metricsData.counters || {};
            let httpRequests = 0;
            let httpErrors = 0;

            Object.keys(httpCounters).forEach(key => {
                if (key.includes('http_requests_total')) {
                    httpRequests += httpCounters[key];
                }
                if (key.includes('http_responses_total') && (key.includes('status="5') || key.includes('_5'))) {
                    httpErrors += httpCounters[key];
                }
            });

            // Scan metrics
            let scanSuccess = 0;
            let scanFailures = 0;

            Object.keys(httpCounters).forEach(key => {
                if (key.includes('scanner_scans_success_total')) {
                    scanSuccess += httpCounters[key];
                }
                if (key.includes('scanner_scans_failed_total')) {
                    scanFailures += httpCounters[key];
                }
            });

            const totalScans = scanSuccess + scanFailures;
            const successRate = totalScans > 0 ? ((scanSuccess / totalScans) * 100).toFixed(1) : 0;

            // Memory metrics
            const memoryGauges = metricsData.gauges || {};
            let memoryPercent = 0;

            Object.keys(memoryGauges).forEach(key => {
                if (key.includes('memory_usage_percent')) {
                    memoryPercent = memoryGauges[key];
                }
            });

            // Response time metrics
            const responseTimes = metricsData.histograms || {};
            let avgResponseTime = 0;

            Object.keys(responseTimes).forEach(key => {
                if (key.includes('http_request_duration_seconds')) {
                    const values = responseTimes[key];
                    if (values && values.length > 0) {
                        const sum = values.reduce((a, b) => a + b, 0);
                        avgResponseTime = (sum / values.length * 1000).toFixed(0); // Convert to ms
                    }
                }
            });

            const metrics = [
                {
                    title: 'HTTP Requests',
                    value: httpRequests.toLocaleString(),
                    unit: 'total',
                    status: 'good'
                },
                {
                    title: 'HTTP Error Rate',
                    value: httpRequests > 0 ? ((httpErrors / httpRequests) * 100).toFixed(1) : '0.0',
                    unit: '%',
                    status: (httpErrors / Math.max(httpRequests, 1)) > 0.05 ? 'error' : 'good'
                },
                {
                    title: 'Scan Success Rate',
                    value: successRate,
                    unit: '%',
                    status: successRate > 90 ? 'good' : successRate > 70 ? 'warning' : 'error'
                },
                {
                    title: 'Total Scans',
                    value: totalScans.toLocaleString(),
                    unit: 'completed',
                    status: 'good'
                },
                {
                    title: 'Memory Usage',
                    value: memoryPercent.toFixed(1),
                    unit: '%',
                    status: memoryPercent > 85 ? 'error' : memoryPercent > 70 ? 'warning' : 'good'
                },
                {
                    title: 'Avg Response Time',
                    value: avgResponseTime,
                    unit: 'ms',
                    status: avgResponseTime > 5000 ? 'error' : avgResponseTime > 2000 ? 'warning' : 'good'
                }
            ];

            grid.innerHTML = metrics.map(metric => `
                <div class="metric-card">
                    <div class="metric-title">${metric.title}</div>
                    <div class="metric-value status-${metric.status}">${metric.value}<span class="metric-unit"> ${metric.unit}</span></div>
                </div>
            `).join('');
        }

        function updateAlerts() {
            const alertsList = document.getElementById('alerts-list');

            if (alertsData.length === 0) {
                alertsList.innerHTML = '<p style="color: #666; font-style: italic;">No active alerts</p>';
                return;
            }

            alertsList.innerHTML = alertsData.map(alert => `
                <div class="alert-item alert-${alert.severity.toLowerCase()}">
                    <strong>${alert.name}</strong>: ${alert.description}
                    <br><small>${new Date(alert.timestamp * 1000).toLocaleString()}</small>
                </div>
            `).join('');
        }

        function updateLogs(filter = 'recent', search = '') {
            const logsList = document.getElementById('logs-list');

            if (!logsData.logs || logsData.logs.length === 0) {
                logsList.innerHTML = '<p style="color: #666; font-style: italic;">No logs available</p>';
                return;
            }

            let filteredLogs = logsData.logs;

            // Apply filter
            switch (filter) {
                case 'errors':
                    filteredLogs = filteredLogs.filter(log => log.level === 'ERROR');
                    break;
                case 'warnings':
                    filteredLogs = filteredLogs.filter(log => log.level === 'WARNING');
                    break;
                case 'api':
                    filteredLogs = filteredLogs.filter(log => log.component === 'api_server');
                    break;
            }

            // Apply search
            if (search) {
                filteredLogs = filteredLogs.filter(log =>
                    log.message && log.message.toLowerCase().includes(search)
                );
            }

            logsList.innerHTML = filteredLogs.slice(0, 50).map(log => {
                const timestamp = new Date(log.timestamp).toLocaleString();
                const correlationId = log.correlation ? log.correlation.correlation_id : 'N/A';
                return `
                    <div class="log-item log-${log.level}">
                        <strong>${log.level}</strong> [${log.component}] ${timestamp}
                        <br><small>Correlation: ${correlationId.substring(0, 8)}...</small>
                        <br>${log.message}
                    </div>
                `;
            }).join('');
        }

        function updateTimestamp() {
            const timestamp = document.getElementById('last-updated');
            timestamp.textContent = `Last updated: ${new Date().toLocaleString()}`;
        }

        // Auto-refresh every 30 seconds
        setInterval(fetchData, 30000);

        // Initial load
        fetchData();
    </script>
</body>
</html>
"""

def get_dashboard_html() -> str:
    """Get the dashboard HTML template."""
    return DASHBOARD_HTML

def get_dashboard_data() -> Dict[str, Any]:
    """Get current metrics and alerts data for the dashboard."""
    if not DASHBOARD_AVAILABLE:
        return {"error": "Dashboard not available"}

    try:
        metrics_collector = get_metrics_collector()
        alert_manager = get_alert_manager()

        metrics_data = metrics_collector.get_metrics_data()

        # Get active alerts
        active_alerts = []
        if hasattr(alert_manager, 'active_alerts'):
            active_alerts = [
                {
                    "alert_id": alert.alert_id,
                    "name": alert.name,
                    "description": alert.description,
                    "severity": alert.severity.value,
                    "timestamp": alert.timestamp
                }
                for alert in alert_manager.active_alerts.values()
            ]

        return {
            "metrics": metrics_data,
            "alerts": active_alerts,
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

def create_dashboard_routes(app):
    """Add dashboard routes to FastAPI app."""

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard():
        """Serve the main dashboard page."""
        if not DASHBOARD_AVAILABLE:
            return HTMLResponse("<h1>Dashboard Not Available</h1><p>Dashboard module not loaded.</p>")

        html_content = get_dashboard_html()
        return HTMLResponse(html_content)

    @app.get("/api/dashboard/metrics")
    async def get_metrics_api():
        """API endpoint for metrics data."""
        if not DASHBOARD_AVAILABLE:
            return {"error": "Dashboard not available"}

        try:
            metrics_collector = get_metrics_collector()
            return metrics_collector.get_metrics_data()
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/dashboard/alerts")
    async def get_alerts_api():
        """API endpoint for alerts data."""
        if not DASHBOARD_AVAILABLE:
            return []

        try:
            alert_manager = get_alert_manager()
            active_alerts = []
            if hasattr(alert_manager, 'active_alerts'):
                active_alerts = [
                    {
                        "alert_id": alert.alert_id,
                        "name": alert.name,
                        "description": alert.description,
                        "severity": alert.severity.value,
                        "timestamp": alert.timestamp
                    }
                    for alert in alert_manager.active_alerts.values()
                ]
            return active_alerts
        except Exception as e:
            return []

    @app.get("/api/dashboard/health")
    async def dashboard_health():
        """Health check for dashboard."""
        return {
            "status": "healthy" if DASHBOARD_AVAILABLE else "unavailable",
            "timestamp": time.time()
        }

    # Optional logging aggregation imports
    try:
        from .logging_aggregation import get_log_aggregator, LOGGING_AGGREGATION_AVAILABLE
        if LOGGING_AGGREGATION_AVAILABLE:
            @app.get("/api/dashboard/logs")
            async def get_logs_api(limit: int = 50):
                """API endpoint for logs data."""
                try:
                    aggregator = get_log_aggregator()
                    logs = aggregator.get_recent_logs(limit)
                    return {"logs": logs, "count": len(logs)}
                except Exception as e:
                    return {"error": str(e)}
    except ImportError:
        pass