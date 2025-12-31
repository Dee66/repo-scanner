"""Resource Management and Graceful Degradation Module.

Provides configurable resource limits, monitoring, and graceful degradation
for the Repository Intelligence Scanner to maintain operational stability.
"""

import os
import time
import logging
import threading
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
import psutil

logger = logging.getLogger(__name__)

class DegradationLevel(Enum):
    """Levels of resource degradation."""
    NORMAL = "normal"
    LIGHT = "light"
    HEAVY = "heavy"
    CRITICAL = "critical"

class ResourceManager:
    """Manages resource monitoring and graceful degradation."""

    def __init__(self):
        self.process = psutil.Process()
        self.degradation_level = DegradationLevel.NORMAL
        self.degradation_callbacks: List[Callable[[DegradationLevel], None]] = []
        self.monitoring_active = False
        self._stop_event: Optional[threading.Event] = None
        self.monitor_thread: Optional[threading.Thread] = None

        # Configurable thresholds for degradation (as percentage of limits)
        self.degradation_thresholds = {
            DegradationLevel.LIGHT: {
                "memory_percent": 70,  # 70% of memory limit
                "cpu_percent": 60,     # 60% of CPU limit
            },
            DegradationLevel.HEAVY: {
                "memory_percent": 85,  # 85% of memory limit
                "cpu_percent": 75,     # 75% of CPU limit
            },
            DegradationLevel.CRITICAL: {
                "memory_percent": 95,  # 95% of memory limit
                "cpu_percent": 90,     # 90% of CPU limit
            }
        }

        # Resource limits from environment or defaults
        self.resource_limits = {
            "max_memory_mb": int(os.getenv("REPO_SCANNER_MAX_MEMORY_MB", "2048")),
            "max_cpu_percent": int(os.getenv("REPO_SCANNER_MAX_CPU_PERCENT", "80")),
        }

    def add_degradation_callback(self, callback: Callable[[DegradationLevel], None]):
        """Add a callback to be called when degradation level changes."""
        self.degradation_callbacks.append(callback)

    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage statistics."""
        try:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            cpu_percent = psutil.cpu_percent(interval=1.0)  # Increased interval for more stable readings

            memory_limit_percent = (memory_mb / self.resource_limits["max_memory_mb"]) * 100
            cpu_limit_percent = (cpu_percent / self.resource_limits["max_cpu_percent"]) * 100

            return {
                "memory_mb": memory_mb,
                "cpu_percent": cpu_percent,
                "memory_limit_percent": memory_limit_percent,
                "cpu_limit_percent": cpu_limit_percent,
                "memory_limit_exceeded": memory_limit_percent > 100,
                "cpu_limit_exceeded": cpu_limit_percent > 100,
                "degradation_level": self.degradation_level.value,
                "timestamp": time.time()
            }
        except Exception as e:
            logger.warning(f"Failed to get resource usage: {e}")
            return {
                "memory_mb": 0,
                "cpu_percent": 0,
                "memory_limit_percent": 0,
                "cpu_limit_percent": 0,
                "memory_limit_exceeded": False,
                "cpu_limit_exceeded": False,
                "degradation_level": self.degradation_level.value,
                "timestamp": time.time()
            }

    def _determine_degradation_level(self, usage: Dict[str, Any]) -> DegradationLevel:
        """Determine the appropriate degradation level based on resource usage."""
        memory_percent = usage["memory_limit_percent"]
        cpu_percent = usage["cpu_limit_percent"]

        # Check for critical first (most restrictive)
        if (memory_percent >= self.degradation_thresholds[DegradationLevel.CRITICAL]["memory_percent"] or
            cpu_percent >= self.degradation_thresholds[DegradationLevel.CRITICAL]["cpu_percent"]):
            return DegradationLevel.CRITICAL

        # Check for heavy
        if (memory_percent >= self.degradation_thresholds[DegradationLevel.HEAVY]["memory_percent"] or
            cpu_percent >= self.degradation_thresholds[DegradationLevel.HEAVY]["cpu_percent"]):
            return DegradationLevel.HEAVY

        # Check for light
        if (memory_percent >= self.degradation_thresholds[DegradationLevel.LIGHT]["memory_percent"] or
            cpu_percent >= self.degradation_thresholds[DegradationLevel.LIGHT]["cpu_percent"]):
            return DegradationLevel.LIGHT

        return DegradationLevel.NORMAL

    def _trigger_degradation(self, new_level: DegradationLevel):
        """Trigger degradation actions when level changes."""
        if new_level != self.degradation_level:
            old_level = self.degradation_level
            self.degradation_level = new_level

            logger.info(f"Resource degradation level changed: {old_level.value} -> {new_level.value}")

            # Call all registered callbacks
            for callback in self.degradation_callbacks:
                try:
                    callback(new_level)
                except Exception as e:
                    logger.error(f"Error in degradation callback: {e}")

    def _monitor_resources(self):
        """Background monitoring thread."""
        logger.info("Starting resource monitoring")
        check_interval = 2.0  # Check every 2 seconds

        while not self._stop_event.is_set():
            try:
                usage = self.get_resource_usage()
                new_level = self._determine_degradation_level(usage)

                # Log resource usage periodically
                if int(time.time()) % 30 == 0:  # Log every 30 seconds
                    logger.info(f"Resource usage - Memory: {usage['memory_mb']:.1f}MB "
                              f"({usage['memory_limit_percent']:.1f}%), "
                              f"CPU: {usage['cpu_percent']:.1f}% "
                              f"({usage['cpu_limit_percent']:.1f}%), "
                              f"Degradation: {usage['degradation_level']}")

                self._trigger_degradation(new_level)

                # If critical, force garbage collection
                if new_level == DegradationLevel.CRITICAL:
                    import gc
                    gc.collect()
                    logger.warning("Critical resource usage - triggered garbage collection")

            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")

            self._stop_event.wait(check_interval)

        logger.info("Resource monitoring stopped")

    def start_monitoring(self):
        """Start background resource monitoring."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self._stop_event = threading.Event()
        self.monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitor_thread.start()
        logger.info("Resource monitoring started")

    def stop_monitoring(self):
        """Stop background resource monitoring."""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        self._stop_event.set()

        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
            logger.info("Resource monitoring stopped")

    def get_degradation_config(self) -> Dict[str, Any]:
        """Get configuration for current degradation level."""
        configs = {
            DegradationLevel.NORMAL: {
                "max_threads": 4,
                "batch_size": 50,
                "skip_optional_stages": False,
                "use_lightweight_parsing": False,
            },
            DegradationLevel.LIGHT: {
                "max_threads": 2,
                "batch_size": 25,
                "skip_optional_stages": False,
                "use_lightweight_parsing": False,
            },
            DegradationLevel.HEAVY: {
                "max_threads": 1,
                "batch_size": 10,
                "skip_optional_stages": True,
                "use_lightweight_parsing": True,
            },
            DegradationLevel.CRITICAL: {
                "max_threads": 1,
                "batch_size": 5,
                "skip_optional_stages": True,
                "use_lightweight_parsing": True,
            }
        }
        return configs[self.degradation_level]

# Global resource manager instance
_resource_manager: Optional[ResourceManager] = None

def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance."""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager

def start_global_resource_monitoring():
    """Start global resource monitoring."""
    manager = get_resource_manager()
    manager.start_monitoring()

def stop_global_resource_monitoring():
    """Stop global resource monitoring."""
    manager = get_resource_manager()
    manager.stop_monitoring()