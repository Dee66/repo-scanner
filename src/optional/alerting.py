"""Alerting system for performance degradation and error monitoring."""

import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import os

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    RESOLVED = "resolved"

@dataclass
class Alert:
    """Alert data structure."""
    alert_id: str
    name: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    timestamp: float
    labels: Dict[str, str]
    value: Any = None
    threshold: Any = None

class AlertRule:
    """Alert rule definition."""
    def __init__(self, name: str, description: str, severity: AlertSeverity,
                 condition: Callable, threshold: Any, labels: Dict[str, str] = None):
        self.name = name
        self.description = description
        self.severity = severity
        self.condition = condition
        self.threshold = threshold
        self.labels = labels or {}
        self.last_triggered = 0
        self.cooldown_seconds = 300  # 5 minutes cooldown

    def should_trigger(self, metrics_data: Dict[str, Any]) -> Optional[Alert]:
        """Check if this rule should trigger an alert."""
        current_time = time.time()

        # Check cooldown
        if current_time - self.last_triggered < self.cooldown_seconds:
            return None

        # Evaluate condition
        try:
            if self.condition(metrics_data, self.threshold):
                self.last_triggered = current_time
                return Alert(
                    alert_id=f"{self.name}_{int(current_time)}",
                    name=self.name,
                    description=self.description,
                    severity=self.severity,
                    status=AlertStatus.ACTIVE,
                    timestamp=current_time,
                    labels=self.labels.copy(),
                    threshold=self.threshold
                )
        except Exception as e:
            logger.error(f"Error evaluating alert rule {self.name}: {e}")

        return None

class AlertManager:
    """Manages alerting rules and alert dispatching."""

    def __init__(self):
        self.rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable[[Alert], None]] = []
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = False

        # Add default console handler
        self.add_alert_handler(self._console_alert_handler)

    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules.append(rule)
        logger.info(f"Added alert rule: {rule.name}")

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler function."""
        self.alert_handlers.append(handler)

    def _console_alert_handler(self, alert: Alert):
        """Default console alert handler."""
        severity_color = {
            AlertSeverity.LOW: "🟢",
            AlertSeverity.MEDIUM: "🟡",
            AlertSeverity.HIGH: "🟠",
            AlertSeverity.CRITICAL: "🔴"
        }

        color = severity_color.get(alert.severity, "⚪")
        status_emoji = "🚨" if alert.status == AlertStatus.ACTIVE else "✅"

        message = f"{color} {status_emoji} ALERT [{alert.severity.value.upper()}] {alert.name}: {alert.description}"

        if alert.value is not None:
            message += f" (value: {alert.value})"

        if alert.threshold is not None:
            message += f" (threshold: {alert.threshold})"

        logger.warning(message)
        print(message)  # Also print to stdout for visibility

    def evaluate_rules(self, metrics_data: Dict[str, Any]):
        """Evaluate all alert rules against current metrics."""
        for rule in self.rules:
            alert = rule.should_trigger(metrics_data)
            if alert:
                self._handle_alert(alert)

    def _handle_alert(self, alert: Alert):
        """Handle a triggered alert."""
        alert_key = f"{alert.name}_{alert.labels.get('instance', 'default')}"

        if alert.status == AlertStatus.ACTIVE:
            if alert_key not in self.active_alerts:
                self.active_alerts[alert_key] = alert
                # Dispatch to all handlers
                for handler in self.alert_handlers:
                    try:
                        handler(alert)
                    except Exception as e:
                        logger.error(f"Error in alert handler: {e}")
        else:
            # Resolved alert
            if alert_key in self.active_alerts:
                del self.active_alerts[alert_key]
                # Dispatch resolved alert
                for handler in self.alert_handlers:
                    try:
                        handler(alert)
                    except Exception as e:
                        logger.error(f"Error in alert handler: {e}")

    def start_monitoring(self, metrics_collector, interval_seconds: int = 60):
        """Start background monitoring thread."""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            logger.warning("Alert monitoring already running")
            return

        self._stop_monitoring = False
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(metrics_collector, interval_seconds),
            daemon=True
        )
        self._monitoring_thread.start()
        logger.info(f"Started alert monitoring with {interval_seconds}s interval")

    def stop_monitoring(self):
        """Stop background monitoring."""
        self._stop_monitoring = True
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("Stopped alert monitoring")

    def _monitoring_loop(self, metrics_collector, interval_seconds: int):
        """Background monitoring loop."""
        while not self._stop_monitoring:
            try:
                metrics_data = metrics_collector.get_metrics_data()
                self.evaluate_rules(metrics_data)
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}")

            time.sleep(interval_seconds)

# Global alert manager instance
_alert_manager = None

def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
        _setup_default_rules(_alert_manager)
    return _alert_manager

def _setup_default_rules(alert_manager: AlertManager):
    """Set up default alerting rules."""

    # High error rate alert
    def high_error_rate_condition(metrics_data, threshold):
        counters = metrics_data.get('counters', {})
        http_requests = 0
        http_errors = 0

        # Count total HTTP requests and errors
        for key, value in counters.items():
            if 'http_requests_total' in key:
                http_requests += value
            elif 'http_responses_total' in key and ('status="5' in key or '_5' in key):
                http_errors += value

        if http_requests > 0:
            error_rate = http_errors / http_requests
            return error_rate > threshold
        return False

    alert_manager.add_rule(AlertRule(
        name="high_error_rate",
        description="HTTP error rate exceeds threshold",
        severity=AlertSeverity.HIGH,
        condition=high_error_rate_condition,
        threshold=0.05,  # 5% error rate
        labels={"component": "api_server"}
    ))

    # Slow response time alert
    def slow_response_condition(metrics_data, threshold):
        histograms = metrics_data.get('histograms', {})
        for key, values in histograms.items():
            if 'http_request_duration_seconds' in key:
                if values and len(values) > 0:
                    # Use 95th percentile approximation (near max)
                    sorted_values = sorted(values)
                    p95_index = int(len(sorted_values) * 0.95)
                    p95 = sorted_values[min(p95_index, len(sorted_values) - 1)]
                    return p95 > threshold
        return False

    alert_manager.add_rule(AlertRule(
        name="slow_response_time",
        description="95th percentile response time exceeds threshold",
        severity=AlertSeverity.MEDIUM,
        condition=slow_response_condition,
        threshold=5.0,  # 5 seconds
        labels={"component": "api_server"}
    ))

    # High memory usage alert
    def high_memory_condition(metrics_data, threshold):
        gauges = metrics_data.get('gauges', {})
        for key, value in gauges.items():
            if 'memory_usage_percent' in key:
                return value > threshold
        return False

    alert_manager.add_rule(AlertRule(
        name="high_memory_usage",
        description="Memory usage exceeds threshold",
        severity=AlertSeverity.MEDIUM,
        condition=high_memory_condition,
        threshold=85.0,  # 85%
        labels={"component": "system"}
    ))

    # Scan failure rate alert
    def scan_failure_condition(metrics_data, threshold):
        counters = metrics_data.get('counters', {})
        scan_success = 0
        scan_failures = 0

        for key, value in counters.items():
            if 'scanner_scans_success_total' in key:
                scan_success += value
            elif 'scanner_scans_failed_total' in key:
                scan_failures += value

        total_scans = scan_success + scan_failures

        if total_scans > 0:
            failure_rate = scan_failures / total_scans
            return failure_rate > threshold
        return False

    alert_manager.add_rule(AlertRule(
        name="scan_failure_rate",
        description="Scan failure rate exceeds threshold",
        severity=AlertSeverity.HIGH,
        condition=scan_failure_condition,
        threshold=0.10,  # 10% failure rate
        labels={"component": "analysis"}
    ))

    logger.info("Set up default alerting rules")