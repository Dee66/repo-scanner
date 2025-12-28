"""Prometheus-compatible metrics collection for monitoring and observability."""

import time
import threading
import json
import os
from collections import defaultdict, deque
from typing import Dict, Any, List, Optional
import psutil

class MetricsCollector:
    """Collects and exposes Prometheus-compatible metrics."""

    def __init__(self):
        self.metrics = defaultdict(lambda: defaultdict(float))
        self.histograms = defaultdict(lambda: defaultdict(list))
        self.counters = defaultdict(float)
        self.gauges = defaultdict(float)
        self.histogram_buckets = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0]
        self._lock = threading.Lock()

    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self._lock:
            key = self._make_key(name, labels)
            self.counters[key] += value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        with self._lock:
            key = self._make_key(name, labels)
            self.gauges[key] = value

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a value in a histogram."""
        with self._lock:
            key = self._make_key(name, labels)
            if key not in self.histograms:
                self.histograms[key] = deque(maxlen=1000)  # Keep last 1000 observations
            self.histograms[key].append(value)

    def record_operation_time(self, operation: str, duration: float, labels: Optional[Dict[str, str]] = None):
        """Record operation execution time."""
        self.observe_histogram(f"{operation}_duration_seconds", duration, labels)
        self.increment_counter(f"{operation}_total", labels=labels)

    def record_operation_success(self, operation: str, labels: Optional[Dict[str, str]] = None):
        """Record successful operation."""
        self.increment_counter(f"{operation}_success_total", labels=labels)

    def record_operation_failure(self, operation: str, error_type: str, labels: Optional[Dict[str, str]] = None):
        """Record failed operation."""
        labels = labels or {}
        labels["error_type"] = error_type
        self.increment_counter(f"{operation}_failure_total", labels=labels)

    def collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)  # Don't block
            self.set_gauge("cpu_usage_percent", cpu_percent)

            # Memory metrics
            memory = psutil.virtual_memory()
            self.set_gauge("memory_usage_bytes", memory.used)
            self.set_gauge("memory_total_bytes", memory.total)
            self.set_gauge("memory_usage_percent", memory.percent)

            # Disk metrics
            disk = psutil.disk_usage('/')
            self.set_gauge("disk_usage_bytes", disk.used)
            self.set_gauge("disk_total_bytes", disk.total)
            self.set_gauge("disk_usage_percent", disk.percent)

            # Network metrics (basic)
            net = psutil.net_io_counters()
            self.set_gauge("network_bytes_sent", net.bytes_sent)
            self.set_gauge("network_bytes_recv", net.bytes_recv)

        except Exception:
            # Silently ignore system metric collection failures
            pass

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create a unique key for metric storage."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _format_prometheus_output(self) -> str:
        """Format all metrics in Prometheus exposition format."""
        lines = []
        lines.append("# HELP repo_scanner_metrics Repository Intelligence Scanner Metrics")
        lines.append("# TYPE repo_scanner_metrics gauge")
        lines.append("repo_scanner_metrics 1")
        lines.append("")

        # Counters
        for key, value in self.counters.items():
            name = key.split('{')[0] if '{' in key else key
            lines.append(f"# HELP {name} Counter metric")
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{key} {value}")
            lines.append("")

        # Gauges
        for key, value in self.gauges.items():
            name = key.split('{')[0] if '{' in key else key
            lines.append(f"# HELP {name} Gauge metric")
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{key} {value}")
            lines.append("")

        # Histograms
        for key, values in self.histograms.items():
            if not values:
                continue
            name = key.split('{')[0] if '{' in key else key
            base_name = name.replace("_duration_seconds", "")

            lines.append(f"# HELP {base_name}_duration_seconds Histogram of operation durations")
            lines.append(f"# TYPE {base_name}_duration_seconds histogram")

            # Calculate histogram buckets
            sorted_values = sorted(values)
            total_count = len(sorted_values)

            for bucket in self.histogram_buckets + [float('inf')]:
                count = sum(1 for v in sorted_values if v <= bucket)
                lines.append(f"{base_name}_duration_seconds_bucket{{le=\"{bucket}\"}} {count}")

            lines.append(f"{base_name}_duration_seconds_count {total_count}")
            lines.append(f"{base_name}_duration_seconds_sum {sum(sorted_values)}")
            lines.append("")

        return "\n".join(lines)

    def get_prometheus_metrics(self) -> str:
        """Get all metrics in Prometheus format."""
        if self._lock.acquire(blocking=False):
            try:
                return self._format_prometheus_output()
            finally:
                self._lock.release()
        else:
            # Return basic metrics if can't acquire lock
            return "# HELP repo_scanner_metrics Repository Intelligence Scanner Metrics\n# TYPE repo_scanner_metrics gauge\nrepo_scanner_metrics 1\n"

    def get_metrics_data(self) -> Dict[str, Any]:
        """Get all metrics as a structured data dictionary."""
        if self._lock.acquire(blocking=False):
            try:
                return {
                    "counters": dict(self.counters),
                    "gauges": dict(self.gauges),
                    "histograms": {k: list(v) for k, v in self.histograms.items()},
                    "timestamp": time.time()
                }
            finally:
                self._lock.release()
        else:
            # Return current data if can't acquire lock (avoid deadlock)
            return {
                "counters": {},
                "gauges": {},
                "histograms": {},
                "timestamp": time.time()
            }

    def save_to_file(self, file_path: str = None):
        """Save metrics to a JSON file."""
        if file_path is None:
            file_path = os.path.expanduser("~/.repo_scanner_metrics.json")
        
        # Try to acquire lock with retries to avoid deadlock with background thread
        max_retries = 3
        for attempt in range(max_retries):
            if self._lock.acquire(blocking=False):
                try:
                    # Get data while holding the lock
                    data = {
                        "counters": dict(self.counters),
                        "gauges": dict(self.gauges),
                        "histograms": {k: list(v) for k, v in self.histograms.items()},
                        "timestamp": time.time()
                    }
                    try:
                        with open(file_path, 'w') as f:
                            json.dump(data, f, indent=2)
                        return  # Success
                    except Exception as e:
                        print(f"Warning: Failed to save metrics to {file_path}: {e}")
                        return
                finally:
                    self._lock.release()
            else:
                if attempt < max_retries - 1:
                    time.sleep(0.1)  # Wait 100ms before retry
                else:
                    print("Warning: Could not acquire metrics lock for saving after retries, skipping persistence")

    def load_from_file(self, file_path: str = None):
        """Load metrics from a JSON file."""
        if file_path is None:
            file_path = os.path.expanduser("~/.repo_scanner_metrics.json")
        
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            with self._lock:
                self.counters.update(data.get("counters", {}))
                self.gauges.update(data.get("gauges", {}))
                for key, values in data.get("histograms", {}).items():
                    if key not in self.histograms:
                        self.histograms[key] = deque(maxlen=1000)
                    self.histograms[key].extend(values)
        except Exception as e:
            print(f"Warning: Failed to load metrics from {file_path}: {e}")

# Global metrics collector instance
_metrics_collector = None
_metrics_lock = threading.Lock()

def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        with _metrics_lock:
            if _metrics_collector is None:
                _metrics_collector = MetricsCollector()
                # Load existing metrics from file
                _metrics_collector.load_from_file()
                # Start background system metrics collection
                start_background_metrics_collection()
    return _metrics_collector

def start_background_metrics_collection():
    """Start background collection of system metrics."""
    def collect_metrics():
        collector = get_metrics_collector()
        while True:
            collector.collect_system_metrics()
            time.sleep(60)  # Collect every 60 seconds to reduce lock conflicts

    thread = threading.Thread(target=collect_metrics, daemon=True)
    thread.start()

# Convenience functions for easy metrics recording
def record_operation_start(operation: str, labels: Optional[Dict[str, str]] = None) -> float:
    """Record the start of an operation and return start time."""
    start_time = time.time()
    collector = get_metrics_collector()
    collector.increment_counter(f"{operation}_started_total", labels=labels)
    return start_time

def record_operation_end(operation: str, start_time: float, success: bool = True,
                        error_type: str = None, labels: Optional[Dict[str, str]] = None):
    """Record the end of an operation."""
    duration = time.time() - start_time
    collector = get_metrics_collector()

    collector.record_operation_time(operation, duration, labels)

    if success:
        collector.record_operation_success(operation, labels)
    else:
        collector.record_operation_failure(operation, error_type or "unknown", labels)
    
    # Save metrics to persist across process restarts
    collector.save_to_file()