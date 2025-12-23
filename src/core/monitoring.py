"""Production Monitoring and Observability for Repository Intelligence Scanner."""

import time
import psutil
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from dataclasses import dataclass, field
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """A single metric measurement."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)

@dataclass
class MetricSeries:
    """Time series data for a metric."""
    name: str
    help: str
    type: str  # 'counter', 'gauge', 'histogram'
    points: deque = field(default_factory=lambda: deque(maxlen=1000))

class MetricsCollector:
    """Collects and exposes metrics for monitoring."""

    def __init__(self):
        self.metrics: Dict[str, MetricSeries] = {}
        self.lock = threading.Lock()

        # Initialize core metrics
        self._init_core_metrics()

    def _init_core_metrics(self):
        """Initialize core monitoring metrics."""
        # Scan metrics
        self.create_metric('scanner_scans_total', 'Total number of scans performed', 'counter')
        self.create_metric('scanner_scans_success_total', 'Total number of successful scans', 'counter')
        self.create_metric('scanner_scans_failed_total', 'Total number of failed scans', 'counter')
        self.create_metric('scanner_scan_duration_seconds', 'Scan duration in seconds', 'histogram')

        # Repository metrics
        self.create_metric('scanner_repositories_total', 'Total repositories scanned by type', 'counter', ['repo_type'])
        self.create_metric('scanner_files_processed_total', 'Total files processed', 'counter')

        # Performance metrics
        self.create_metric('scanner_memory_usage_mb', 'Current memory usage in MB', 'gauge')
        self.create_metric('scanner_cpu_usage_percent', 'Current CPU usage percentage', 'gauge')
        self.create_metric('scanner_active_jobs', 'Number of currently active scan jobs', 'gauge')

        # Error metrics
        self.create_metric('scanner_errors_total', 'Total errors by type', 'counter', ['error_type'])

        # API metrics
        self.create_metric('api_requests_total', 'Total API requests', 'counter', ['method', 'endpoint', 'status'])
        self.create_metric('api_request_duration_seconds', 'API request duration', 'histogram', ['method', 'endpoint'])

    def create_metric(self, name: str, help: str, type: str, label_names: List[str] = None):
        """Create a new metric."""
        if label_names is None:
            label_names = []

        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = MetricSeries(name=name, help=help, type=type)

    def increment(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric."""
        if labels is None:
            labels = {}

        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            labels=labels
        )

        with self.lock:
            if name in self.metrics:
                self.metrics[name].points.append(point)

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value."""
        if labels is None:
            labels = {}

        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            labels=labels
        )

        with self.lock:
            if name in self.metrics:
                self.metrics[name].points.append(point)

    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a histogram metric value."""
        if labels is None:
            labels = {}

        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            labels=labels
        )

        with self.lock:
            if name in self.metrics:
                self.metrics[name].points.append(point)

    def get_metrics(self) -> Dict[str, Any]:
        """Get all current metric values."""
        result = {}

        with self.lock:
            for name, series in self.metrics.items():
                if series.points:
                    latest_point = series.points[-1]
                    result[name] = {
                        'value': latest_point.value,
                        'timestamp': latest_point.timestamp,
                        'labels': latest_point.labels,
                        'help': series.help,
                        'type': series.type
                    }

        return result

    def get_metric_history(self, name: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get historical data for a metric."""
        cutoff = time.time() - (hours * 3600)
        result = []

        with self.lock:
            if name in self.metrics:
                for point in self.metrics[name].points:
                    if point.timestamp >= cutoff:
                        result.append({
                            'timestamp': point.timestamp,
                            'value': point.value,
                            'labels': point.labels
                        })

        return result

    async def record_scan_completion(self, scan_result: Dict[str, Any]):
        """Record a successful scan completion."""
        self.increment_counter('scanner_scans_total')
        self.increment_counter('scanner_scans_success_total')
        self.increment_counter('scanner_files_processed_total',
                              labels={'count': str(scan_result.get('files_analyzed', 0))})

        execution_time = scan_result.get('execution_time', 0)
        self.observe_histogram('scanner_scan_duration_seconds', execution_time)

    async def record_scan_failure(self, failure_info: Dict[str, Any]):
        """Record a scan failure."""
        self.increment_counter('scanner_scans_total')
        self.increment_counter('scanner_scans_failed_total')

    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect current system and application metrics."""
        # Get current metrics
        metrics = self.get_metrics()

        # Add computed metrics
        current_time = time.time()

        # Calculate rates and averages
        scan_total = metrics.get('scanner_scans_total', {}).get('value', 0)
        scan_success = metrics.get('scanner_scans_success_total', {}).get('value', 0)
        scan_failed = metrics.get('scanner_scans_failed_total', {}).get('value', 0)

        if scan_total > 0:
            success_rate = scan_success / scan_total
            failure_rate = scan_failed / scan_total
        else:
            success_rate = 0
            failure_rate = 0

        # Get system metrics
        system_metrics = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'success_rate': success_rate,
            'failure_rate': failure_rate,
            'error_rate': failure_rate,  # Simplified
            'scan_failure_rate': failure_rate
        }

        # Calculate average scan time from histogram
        scan_times = self.get_metric_history('scanner_scan_duration_seconds', hours=1)
        if scan_times:
            avg_scan_time = sum(point['value'] for point in scan_times) / len(scan_times)
        else:
            avg_scan_time = 0

        system_metrics['avg_scan_time'] = avg_scan_time

        # Check alerts
        alert_manager = get_alert_manager()
        alert_manager.check_alerts(system_metrics)

        # Combine all metrics
        result = {
            'timestamp': current_time,
            'system': system_metrics,
            'application': metrics
        }

        return result

class HealthChecker:
    """Comprehensive health checking for the scanner."""

    def __init__(self):
        self.last_health_check = 0
        self.health_cache = {}
        self.cache_ttl = 30  # seconds

    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        now = time.time()

        # Use cached result if recent
        if now - self.last_health_check < self.cache_ttl:
            return self.health_cache

        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {},
            'overall_healthy': True
        }

        # System resource checks
        health_status['checks']['cpu'] = self._check_cpu()
        health_status['checks']['memory'] = self._check_memory()
        health_status['checks']['disk'] = self._check_disk()

        # Application checks
        health_status['checks']['imports'] = self._check_imports()
        health_status['checks']['database'] = self._check_database()

        # Determine overall health
        for check_name, check_result in health_status['checks'].items():
            if not check_result.get('healthy', True):
                health_status['overall_healthy'] = False
                health_status['status'] = 'unhealthy'

        self.last_health_check = now
        self.health_cache = health_status

        return health_status

    def _check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            return {
                'healthy': cpu_percent < 90,
                'value': cpu_percent,
                'unit': 'percent',
                'threshold': 90
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            return {
                'healthy': memory.percent < 85,
                'value': memory.percent,
                'unit': 'percent',
                'threshold': 85,
                'details': {
                    'used_mb': memory.used / 1024 / 1024,
                    'total_mb': memory.total / 1024 / 1024
                }
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_disk(self) -> Dict[str, Any]:
        """Check disk usage."""
        try:
            disk = psutil.disk_usage('/')
            return {
                'healthy': disk.percent < 90,
                'value': disk.percent,
                'unit': 'percent',
                'threshold': 90,
                'details': {
                    'used_gb': disk.used / 1024 / 1024 / 1024,
                    'total_gb': disk.total / 1024 / 1024 / 1024
                }
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_imports(self) -> Dict[str, Any]:
        """Check that core imports work."""
        try:
            import src.core.pipeline.analysis
            import src.core.quality.output_contract
            return {
                'healthy': True,
                'message': 'Core imports successful'
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity (placeholder for future DB integration)."""
        # For now, just check if we can access the job storage
        try:
            # This would be replaced with actual DB checks when implemented
            return {
                'healthy': True,
                'message': 'In-memory storage accessible'
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

class PerformanceMonitor:
    """Monitors performance metrics."""

    def __init__(self):
        self.request_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.active_operations = {}  # Track active operations

    def start_operation(self, operation: str, metadata: Dict[str, Any] = None):
        """Start tracking an operation."""
        if metadata is None:
            metadata = {}
        
        self.active_operations[operation] = {
            'start_time': time.time(),
            'metadata': metadata
        }

    def complete_operation(self, operation: str, result_metadata: Dict[str, Any] = None):
        """Complete tracking an operation."""
        if operation not in self.active_operations:
            return
        
        start_info = self.active_operations[operation]
        duration = time.time() - start_info['start_time']
        
        # Record the timing
        self.request_times[operation].append(duration)
        
        # Keep only recent measurements (last 100)
        if len(self.request_times[operation]) > 100:
            self.request_times[operation].pop(0)
        
        # Clean up
        del self.active_operations[operation]

    @contextmanager
    def measure_time(self, operation: str):
        """Context manager to measure operation time."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.request_times[operation].append(duration)

            # Keep only recent measurements (last 100)
            if len(self.request_times[operation]) > 100:
                self.request_times[operation].pop(0)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = {}

        for operation, times in self.request_times.items():
            if times:
                stats[operation] = {
                    'count': len(times),
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'p95_time': sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else max(times)
                }

        return stats

    def record_error(self, error_type: str):
        """Record an error occurrence."""
        self.error_counts[error_type] += 1

    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics."""
        return dict(self.error_counts)

@dataclass
class Alert:
    """An alert definition."""
    id: str
    name: str
    description: str
    severity: str  # 'critical', 'warning', 'info'
    condition: str
    threshold: Any
    current_value: Any = None
    triggered_at: Optional[float] = None
    resolved_at: Optional[float] = None
    active: bool = False

class AlertManager:
    """Manages alerts and notifications."""

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.lock = threading.Lock()

        # Initialize default alerts
        self._init_default_alerts()

    def _init_default_alerts(self):
        """Initialize default alert definitions."""
        self.create_alert(
            "high_error_rate",
            "High Error Rate",
            "Error rate exceeds threshold",
            "warning",
            "error_rate > 0.1",
            0.1
        )

        self.create_alert(
            "memory_usage_high",
            "High Memory Usage",
            "Memory usage exceeds 80%",
            "critical",
            "memory_percent > 80",
            80
        )

        self.create_alert(
            "scan_failures_high",
            "High Scan Failure Rate",
            "Scan failure rate exceeds 20%",
            "warning",
            "failure_rate > 0.2",
            0.2
        )

        self.create_alert(
            "performance_degraded",
            "Performance Degraded",
            "Average scan time exceeds 30 seconds",
            "warning",
            "avg_scan_time > 30",
            30
        )

    def create_alert(self, id: str, name: str, description: str, severity: str,
                    condition: str, threshold: Any):
        """Create a new alert definition."""
        with self.lock:
            alert = Alert(
                id=id,
                name=name,
                description=description,
                severity=severity,
                condition=condition,
                threshold=threshold
            )
            self.alerts[id] = alert

    def check_alerts(self, metrics: Dict[str, Any]):
        """Check all alerts against current metrics."""
        with self.lock:
            for alert in self.alerts.values():
                self._check_alert(alert, metrics)

    def _check_alert(self, alert: Alert, metrics: Dict[str, Any]):
        """Check a single alert condition."""
        try:
            # Simple threshold-based checking for now
            if alert.id == "high_error_rate":
                error_rate = metrics.get('error_rate', 0)
                if error_rate > alert.threshold and not alert.active:
                    self._trigger_alert(alert, error_rate)
                elif error_rate <= alert.threshold and alert.active:
                    self._resolve_alert(alert)

            elif alert.id == "memory_usage_high":
                memory_percent = metrics.get('memory_percent', 0)
                if memory_percent > alert.threshold and not alert.active:
                    self._trigger_alert(alert, memory_percent)
                elif memory_percent <= alert.threshold and alert.active:
                    self._resolve_alert(alert)

            elif alert.id == "scan_failures_high":
                failure_rate = metrics.get('scan_failure_rate', 0)
                if failure_rate > alert.threshold and not alert.active:
                    self._trigger_alert(alert, failure_rate)
                elif failure_rate <= alert.threshold and alert.active:
                    self._resolve_alert(alert)

            elif alert.id == "performance_degraded":
                avg_scan_time = metrics.get('avg_scan_time', 0)
                if avg_scan_time > alert.threshold and not alert.active:
                    self._trigger_alert(alert, avg_scan_time)
                elif avg_scan_time <= alert.threshold and alert.active:
                    self._resolve_alert(alert)

        except Exception as e:
            logger.error(f"Error checking alert {alert.id}: {e}")

    def _trigger_alert(self, alert: Alert, current_value: Any):
        """Trigger an alert."""
        alert.active = True
        alert.triggered_at = time.time()
        alert.current_value = current_value
        self.active_alerts[alert.id] = alert

        logger.warning(f"ALERT TRIGGERED: {alert.name} - {alert.description} "
                      f"(value: {current_value}, threshold: {alert.threshold})")

    def _resolve_alert(self, alert: Alert):
        """Resolve an alert."""
        alert.active = False
        alert.resolved_at = time.time()
        self.alert_history.append(alert)
        if alert.id in self.active_alerts:
            del self.active_alerts[alert.id]

        logger.info(f"ALERT RESOLVED: {alert.name}")

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        with self.lock:
            return list(self.active_alerts.values())

    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for the last N hours."""
        cutoff = time.time() - (hours * 3600)
        with self.lock:
            return [alert for alert in self.alert_history
                   if alert.resolved_at and alert.resolved_at > cutoff]

# Global instances
metrics_collector = MetricsCollector()
health_checker = HealthChecker()
performance_monitor = PerformanceMonitor()
alert_manager = AlertManager()

def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    return metrics_collector

def get_health_checker() -> HealthChecker:
    """Get the global health checker."""
    return health_checker

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor."""
    return performance_monitor

def get_alert_manager() -> AlertManager:
    """Get the global alert manager."""
    return alert_manager
