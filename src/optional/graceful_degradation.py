"""Graceful Degradation System for Component Failures.

Implements comprehensive graceful degradation mechanisms to maintain service
availability when components fail, with automatic fallback strategies and
user notifications.
"""

import logging
import time
import threading
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DegradationLevel(Enum):
    """Service degradation levels."""
    FULL_SERVICE = "full"          # All components operational
    LIMITED_SERVICE = "limited"    # Some components degraded, reduced functionality
    EMERGENCY_SERVICE = "emergency"  # Critical components only, minimal functionality
    MAINTENANCE_MODE = "maintenance"  # System unavailable for maintenance


class ComponentStatus(Enum):
    """Component health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a system component."""
    name: str
    status: ComponentStatus = ComponentStatus.UNKNOWN
    last_check: datetime = field(default_factory=datetime.now)
    failure_count: int = 0
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    degradation_level: DegradationLevel = DegradationLevel.FULL_SERVICE

    def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return self.status == ComponentStatus.HEALTHY

    def is_degraded(self) -> bool:
        """Check if component is degraded."""
        return self.status in [ComponentStatus.DEGRADED, ComponentStatus.FAILED]

    def should_degrade(self, max_failures: int = 3) -> bool:
        """Check if component should trigger degradation."""
        return self.consecutive_failures >= max_failures


@dataclass
class DegradationStrategy:
    """Strategy for handling component degradation."""
    component_name: str
    degradation_level: DegradationLevel
    fallback_function: Optional[Callable] = None
    reduced_functionality: Dict[str, Any] = field(default_factory=dict)
    user_message: str = ""
    auto_recovery_timeout: int = 300  # 5 minutes default


class GracefulDegradationManager:
    """Manages graceful degradation of system components."""

    def __init__(self):
        self.components: Dict[str, ComponentHealth] = {}
        self.degradation_strategies: Dict[str, List[DegradationStrategy]] = {}
        self.current_level: DegradationLevel = DegradationLevel.FULL_SERVICE
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_active: bool = False
        self.health_check_interval: int = 30  # seconds
        self.lock = threading.RLock()

    def register_component(self, name: str, health_check_func: Optional[Callable] = None):
        """Register a component for health monitoring."""
        with self.lock:
            self.components[name] = ComponentHealth(name=name)
            if health_check_func:
                self.components[name]._health_check_func = health_check_func

    def register_degradation_strategy(self, strategy: DegradationStrategy):
        """Register a degradation strategy for a component."""
        with self.lock:
            if strategy.component_name not in self.degradation_strategies:
                self.degradation_strategies[strategy.component_name] = []
            self.degradation_strategies[strategy.component_name].append(strategy)
            # Sort by degradation level (most severe first)
            self.degradation_strategies[strategy.component_name].sort(
                key=lambda s: s.degradation_level.value, reverse=True
            )

    def update_component_health(self, name: str, status: ComponentStatus,
                              error: Optional[str] = None):
        """Update the health status of a component."""
        with self.lock:
            if name not in self.components:
                self.register_component(name)

            component = self.components[name]
            component.last_check = datetime.now()
            component.last_error = error

            if status == ComponentStatus.FAILED:
                component.failure_count += 1
                component.consecutive_failures += 1
            elif status == ComponentStatus.HEALTHY:
                component.consecutive_failures = 0
            elif status == ComponentStatus.DEGRADED:
                component.consecutive_failures += 1

            component.status = status

            # Check if we need to trigger degradation
            self._evaluate_degradation()

            logger.info(f"Component {name} health updated: {status.value}")

    def _evaluate_degradation(self):
        """Evaluate overall system degradation level."""
        with self.lock:
            # Count failed/degraded components
            failed_components = sum(1 for c in self.components.values()
                                  if c.status == ComponentStatus.FAILED)
            degraded_components = sum(1 for c in self.components.values()
                                    if c.status == ComponentStatus.DEGRADED)

            total_components = len(self.components)

            # Determine degradation level
            if failed_components > total_components * 0.5:  # More than 50% failed
                new_level = DegradationLevel.EMERGENCY_SERVICE
            elif failed_components > 0 or degraded_components > total_components * 0.3:
                new_level = DegradationLevel.LIMITED_SERVICE
            else:
                new_level = DegradationLevel.FULL_SERVICE

            if new_level != self.current_level:
                self._apply_degradation_level(new_level)

    def _apply_degradation_level(self, level: DegradationLevel):
        """Apply a new degradation level."""
        logger.warning(f"Applying degradation level: {level.value}")

        # Apply component-specific strategies
        for component_name, strategies in self.degradation_strategies.items():
            applicable_strategy = None
            for strategy in strategies:
                if strategy.degradation_level.value <= level.value:
                    applicable_strategy = strategy
                    break

            if applicable_strategy:
                self._apply_strategy(applicable_strategy)

        self.current_level = level

        # Log user-facing message
        self._log_user_notification(level)

    def _apply_strategy(self, strategy: DegradationStrategy):
        """Apply a specific degradation strategy."""
        logger.info(f"Applying degradation strategy for {strategy.component_name}: {strategy.degradation_level.value}")

        # Update component degradation level
        if strategy.component_name in self.components:
            self.components[strategy.component_name].degradation_level = strategy.degradation_level

        # Apply reduced functionality if specified
        if strategy.reduced_functionality:
            # This would typically update global configuration
            logger.info(f"Reduced functionality applied: {strategy.reduced_functionality}")

    def _log_user_notification(self, level: DegradationLevel):
        """Log user-facing notifications about service degradation."""
        messages = {
            DegradationLevel.FULL_SERVICE: "All systems operational",
            DegradationLevel.LIMITED_SERVICE: "Service running with limited functionality due to component issues",
            DegradationLevel.EMERGENCY_SERVICE: "Emergency mode: Only critical functions available",
            DegradationLevel.MAINTENANCE_MODE: "System under maintenance"
        }

        logger.warning(f"SERVICE STATUS: {messages.get(level, 'Unknown status')}")

    def get_service_status(self) -> Dict[str, Any]:
        """Get current service status information."""
        with self.lock:
            component_statuses = {}
            for name, component in self.components.items():
                component_statuses[name] = {
                    "status": component.status.value,
                    "last_check": component.last_check.isoformat(),
                    "failure_count": component.failure_count,
                    "consecutive_failures": component.consecutive_failures,
                    "last_error": component.last_error,
                    "degradation_level": component.degradation_level.value
                }

            return {
                "overall_status": self.current_level.value,
                "components": component_statuses,
                "timestamp": datetime.now().isoformat()
            }

    def start_monitoring(self):
        """Start the health monitoring thread."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Health monitoring started")

    def stop_monitoring(self):
        """Stop the health monitoring thread."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Health monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                self._perform_health_checks()
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")

            time.sleep(self.health_check_interval)

    def _perform_health_checks(self):
        """Perform health checks on all registered components."""
        for name, component in list(self.components.items()):
            if hasattr(component, '_health_check_func'):
                try:
                    health_check_func = getattr(component, '_health_check_func')
                    is_healthy = health_check_func()

                    status = ComponentStatus.HEALTHY if is_healthy else ComponentStatus.FAILED
                    self.update_component_health(name, status)

                except Exception as e:
                    logger.error(f"Health check failed for {name}: {e}")
                    self.update_component_health(name, ComponentStatus.FAILED, str(e))

    def execute_with_degradation(self, component_name: str, operation: Callable,
                               *args, **kwargs) -> Any:
        """Execute an operation with automatic degradation handling."""
        component = self.components.get(component_name)

        if not component or component.is_healthy():
            # Component is healthy, execute normally
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                # Mark component as failed and retry with degradation
                self.update_component_health(component_name, ComponentStatus.FAILED, str(e))
                return self._execute_with_fallback(component_name, operation, e, *args, **kwargs)

        elif component.is_degraded():
            # Component is degraded, use fallback immediately
            return self._execute_with_fallback(component_name, operation, None, *args, **kwargs)

        else:
            # Component failed, use fallback
            return self._execute_with_fallback(component_name, operation, None, *args, **kwargs)

    def _execute_with_fallback(self, component_name: str, operation: Callable,
                             exception: Optional[Exception], *args, **kwargs) -> Any:
        """Execute operation using fallback strategy."""
        strategies = self.degradation_strategies.get(component_name, [])

        for strategy in strategies:
            if strategy.fallback_function:
                try:
                    logger.info(f"Using fallback strategy for {component_name}")
                    return strategy.fallback_function(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback strategy failed for {component_name}: {fallback_error}")
                    continue

        # No fallback worked, raise original exception or a degradation error
        if exception:
            raise exception
        else:
            raise RuntimeError(f"Component {component_name} is unavailable and no fallback available")


# Global degradation manager instance
_degradation_manager = None

def get_degradation_manager() -> GracefulDegradationManager:
    """Get the global graceful degradation manager instance."""
    global _degradation_manager
    if _degradation_manager is None:
        _degradation_manager = GracefulDegradationManager()
    return _degradation_manager


def initialize_graceful_degradation():
    """Initialize the graceful degradation system with default components."""
    manager = get_degradation_manager()

    # Register core components
    manager.register_component("analysis_engine")
    manager.register_component("sme_api")
    manager.register_component("database")
    manager.register_component("file_system")
    manager.register_component("network")
    manager.register_component("external_apis")

    # Register degradation strategies
    manager.register_degradation_strategy(DegradationStrategy(
        component_name="analysis_engine",
        degradation_level=DegradationLevel.LIMITED_SERVICE,
        reduced_functionality={"max_complexity": "medium", "parallel_processing": False},
        user_message="Analysis running with reduced capabilities"
    ))

    manager.register_degradation_strategy(DegradationStrategy(
        component_name="sme_api",
        degradation_level=DegradationLevel.LIMITED_SERVICE,
        fallback_function=lambda *args, **kwargs: {"status": "cached", "data": []},
        user_message="Using cached SME data due to API unavailability"
    ))

    manager.register_degradation_strategy(DegradationStrategy(
        component_name="database",
        degradation_level=DegradationLevel.EMERGENCY_SERVICE,
        fallback_function=lambda *args, **kwargs: None,
        user_message="Database unavailable, operating in offline mode"
    ))

    # Start monitoring
    manager.start_monitoring()

    logger.info("Graceful degradation system initialized")


if __name__ == "__main__":
    # Example usage
    initialize_graceful_degradation()

    manager = get_degradation_manager()

    # Simulate component failure
    manager.update_component_health("analysis_engine", ComponentStatus.FAILED,
                                  "Analysis engine timeout")

    # Check status
    status = manager.get_service_status()
    print(f"Service status: {status['overall_status']}")

    # Cleanup
    manager.stop_monitoring()