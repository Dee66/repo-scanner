"""Production Monitoring and Observability for Repository Intelligence Scanner."""

import time
import psutil
import logging
import asyncio
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from dataclasses import dataclass, field
from contextlib import contextmanager
import os
import sys

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

    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric (alias for increment)."""
        self.increment(name, value, labels)

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
    """Comprehensive health checking for 99.999% uptime monitoring."""

    def __init__(self):
        self.last_health_check = 0
        self.health_cache = {}
        self.cache_ttl = 30  # seconds

        # Uptime tracking for 99.999% SLA
        self.start_time = time.time()
        self.uptime_history = deque(maxlen=1000)  # Track last 1000 health checks
        self.downtime_events = []
        self.last_downtime_start = None

        # Performance thresholds for 99.999% uptime
        self.performance_thresholds = {
            'cpu_percent': 95,  # Max CPU usage
            'memory_percent': 90,  # Max memory usage
            'disk_percent': 95,  # Max disk usage
            'response_time_seconds': 30,  # Max response time
            'error_rate_percent': 0.001,  # Max error rate (0.001% for 99.999%)
        }

        # Dependency health checks
        self.dependency_checks = {
            'circuit_breakers': self._check_circuit_breakers,
            'error_handling': self._check_error_handling,
            'external_apis': self._check_external_apis,
            'filesystem': self._check_filesystem,
            'network': self._check_network,
        }

    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check for 99.999% uptime."""
        now = time.time()

        # Use cached result if recent
        if now - self.last_health_check < self.cache_ttl:
            return self.health_cache

        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': self._calculate_uptime(),
            'sla_compliance': self._check_sla_compliance(),
            'checks': {},
            'overall_healthy': True,
            'version': '1.1.0'
        }

        # System resource checks
        health_status['checks']['cpu'] = self._check_cpu()
        health_status['checks']['memory'] = self._check_memory()
        health_status['checks']['disk'] = self._check_disk()
        health_status['checks']['load_average'] = self._check_load_average()

        # Application checks
        health_status['checks']['imports'] = self._check_imports()
        health_status['checks']['database'] = self._check_database()
        health_status['checks']['configuration'] = self._check_configuration()
        health_status['checks']['circuit_breakers'] = self._check_circuit_breakers()
        health_status['checks']['error_handling'] = self._check_error_handling()

        # External dependency checks
        health_status['checks']['external_apis'] = self._check_external_apis()
        health_status['checks']['filesystem'] = self._check_filesystem()
        health_status['checks']['network'] = self._check_network()

        # Dependency checks
        for dep_name, check_func in self.dependency_checks.items():
            try:
                health_status['checks'][dep_name] = check_func()
            except Exception as e:
                health_status['checks'][dep_name] = {
                    'healthy': False,
                    'error': f'Health check failed: {e}'
                }

        # Performance checks
        health_status['checks']['performance'] = self._check_performance()

        # Determine overall health
        for check_name, check_result in health_status['checks'].items():
            if not check_result.get('healthy', True):
                health_status['overall_healthy'] = False
                health_status['status'] = 'unhealthy'
                self._record_downtime()
                break
        else:
            self._record_uptime()

        # Update cache
        self.last_health_check = now
        self.health_cache = health_status

        return health_status

    def _calculate_uptime(self) -> Dict[str, Any]:
        """Calculate uptime statistics for 99.999% SLA monitoring."""
        total_runtime = time.time() - self.start_time
        healthy_checks = sum(1 for status in self.uptime_history if status)
        total_checks = len(self.uptime_history)

        uptime_percentage = (healthy_checks / max(total_checks, 1)) * 100
        sla_compliant = uptime_percentage >= 99.999  # 99.999% = 5.26 minutes downtime per year

        return {
            'total_seconds': total_runtime,
            'uptime_percentage': uptime_percentage,
            'sla_compliant': sla_compliant,
            'downtime_events': len(self.downtime_events),
            'last_downtime': self.downtime_events[-1] if self.downtime_events else None
        }

    def _check_sla_compliance(self) -> Dict[str, Any]:
        """Check SLA compliance for 99.999% uptime."""
        uptime_info = self._calculate_uptime()

        # Calculate allowed downtime (5.26 minutes per year for 99.999%)
        total_runtime_hours = uptime_info['total_seconds'] / 3600
        allowed_downtime_minutes = total_runtime_hours * (1 - 0.99999) * 60

        actual_downtime_minutes = sum(
            (end - start) for start, end in self.downtime_events
            if end is not None
        ) / 60

        return {
            'compliant': uptime_info['sla_compliant'],
            'uptime_percentage': uptime_info['uptime_percentage'],
            'allowed_downtime_minutes': allowed_downtime_minutes,
            'actual_downtime_minutes': actual_downtime_minutes,
            'remaining_downtime_budget': max(0, allowed_downtime_minutes - actual_downtime_minutes)
        }

    def _record_uptime(self):
        """Record a successful health check."""
        self.uptime_history.append(True)
        if self.last_downtime_start is not None:
            # End current downtime period
            self.downtime_events.append((self.last_downtime_start, time.time()))
            self.last_downtime_start = None

    def _record_downtime(self):
        """Record a failed health check."""
        self.uptime_history.append(False)
        if self.last_downtime_start is None:
            # Start new downtime period
            self.last_downtime_start = time.time()

    async def check_system_health(self) -> Dict[str, Any]:
        """Async wrapper for health check."""
        return self.check_health()

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

    def _check_load_average(self) -> Dict[str, Any]:
        """Check system load average."""
        try:
            load_avg = os.getloadavg()
            cpu_count = os.cpu_count() or 1
            # Consider unhealthy if load average > 2x CPU count
            threshold = cpu_count * 2
            current_load = load_avg[0]  # 1-minute load average

            return {
                'healthy': current_load < threshold,
                'value': current_load,
                'unit': 'load',
                'threshold': threshold,
                'details': {
                    '1min': load_avg[0],
                    '5min': load_avg[1],
                    '15min': load_avg[2],
                    'cpu_count': cpu_count
                }
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_configuration(self) -> Dict[str, Any]:
        """Check configuration validity."""
        try:
            from src.core.system_config import DATA_USAGE_CONFIG
            # Check that critical config values are present and valid
            required_keys = ['limits', 'monitoring', 'performance']
            for key in required_keys:
                if key not in DATA_USAGE_CONFIG:
                    return {
                        'healthy': False,
                        'error': f'Missing required config key: {key}'
                    }

            return {
                'healthy': True,
                'message': 'Configuration valid'
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_circuit_breakers(self) -> Dict[str, Any]:
        """Check circuit breaker health."""
        try:
            from .circuit_breaker import get_circuit_breaker_registry
            registry = get_circuit_breaker_registry()
            metrics = registry.get_all_metrics()

            # Check if any circuit breakers are stuck open
            open_breakers = []
            total_requests = 0
            failed_requests = 0

            for name, breaker_metrics in metrics.items():
                if breaker_metrics['state'] == 'open':
                    open_breakers.append(name)
                total_requests += breaker_metrics['metrics']['total_requests']
                failed_requests += breaker_metrics['metrics']['failed_requests']

            # Consider unhealthy if >50% of breakers are open or error rate >1%
            error_rate = (failed_requests / max(total_requests, 1)) * 100
            too_many_open = len(open_breakers) > len(metrics) * 0.5

            return {
                'healthy': not too_many_open and error_rate < 1.0,
                'total_breakers': len(metrics),
                'open_breakers': open_breakers,
                'error_rate_percent': error_rate,
                'details': metrics
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_error_handling(self) -> Dict[str, Any]:
        """Check error handling system health."""
        try:
            from .error_handling import get_error_handler
            error_handler = get_error_handler()
            metrics = error_handler.get_error_metrics()

            # Check error rates - unhealthy if >0.1% error rate in recent history
            total_errors = metrics.get('total_errors', 0)
            recent_errors = len(metrics.get('recent_errors', []))

            # For 99.999% uptime, we want very low error rates
            error_rate_acceptable = total_errors < 10 or recent_errors < 1

            return {
                'healthy': error_rate_acceptable,
                'total_errors': total_errors,
                'recent_errors': recent_errors,
                'recovery_strategies': len(metrics.get('recovery_strategies', [])),
                'details': metrics
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_external_apis(self) -> Dict[str, Any]:
        """Check external API connectivity (lightweight checks only)."""
        try:
            import requests

            # Quick connectivity check to a reliable external service
            # Using a fast, reliable endpoint that doesn't cost anything
            test_urls = [
                'https://httpbin.org/status/200',  # Free test service
                'https://httpstat.us/200'  # Another free test service
            ]

            for url in test_urls:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        return {
                            'healthy': True,
                            'message': 'External API connectivity confirmed',
                            'response_time_ms': response.elapsed.total_seconds() * 1000
                        }
                except Exception:
                    continue  # Try next URL

            return {
                'healthy': False,
                'error': 'All external API connectivity checks failed'
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_filesystem(self) -> Dict[str, Any]:
        """Check filesystem health."""
        try:
            import tempfile

            # Test write permissions
            with tempfile.NamedTemporaryFile(mode='w', delete=True) as f:
                f.write('test')
                f.flush()

            # Test read permissions on critical directories
            critical_paths = [
                '/tmp',
                os.getcwd(),
                os.path.dirname(sys.executable) if sys.executable else '/usr'
            ]

            for path in critical_paths:
                if os.path.exists(path):
                    try:
                        os.listdir(path)
                    except PermissionError:
                        return {
                            'healthy': False,
                            'error': f'No read permission for {path}'
                        }

            return {
                'healthy': True,
                'message': 'Filesystem access confirmed'
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_network(self) -> Dict[str, Any]:
        """Check basic network connectivity."""
        try:
            import socket

            # Test DNS resolution
            socket.gethostbyname('google.com')

            # Test basic connectivity
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('8.8.8.8', 53))  # Google DNS
            sock.close()

            return {
                'healthy': result == 0,
                'message': 'Network connectivity confirmed' if result == 0 else 'Network connectivity failed'
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }

    def _check_performance(self) -> Dict[str, Any]:
        """Check system performance against thresholds."""
        try:
            # Get current metrics
            cpu_check = self._check_cpu()
            memory_check = self._check_memory()
            load_check = self._check_load_average()

            # Check against performance thresholds
            cpu_healthy = cpu_check['value'] < self.performance_thresholds['cpu_percent']
            memory_healthy = memory_check['value'] < self.performance_thresholds['memory_percent']
            load_healthy = load_check['healthy']

            overall_healthy = cpu_healthy and memory_healthy and load_healthy

            return {
                'healthy': overall_healthy,
                'cpu_usage': cpu_check['value'],
                'memory_usage': memory_check['value'],
                'load_average': load_check['value'],
                'thresholds': self.performance_thresholds
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
