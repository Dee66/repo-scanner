"""Blue-Green Deployment Strategy for Repository Intelligence Scanner.

Implements zero-downtime deployment with automatic rollback capabilities
and traffic switching between blue and green environments.
"""

import os
import time
import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)


@dataclass
class DeploymentEnvironment:
    """Represents a deployment environment (blue or green)."""
    name: str
    version: str
    status: str = "inactive"  # inactive, deploying, active, failed
    health_url: str = ""
    traffic_weight: int = 0  # 0-100
    deployed_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    health_status: str = "unknown"

    def is_healthy(self) -> bool:
        """Check if environment is healthy."""
        return self.health_status == "healthy"

    def is_active(self) -> bool:
        """Check if environment is currently active."""
        return self.status == "active"


@dataclass
class BlueGreenDeployment:
    """Manages blue-green deployment state and operations."""
    blue_env: DeploymentEnvironment
    green_env: DeploymentEnvironment
    current_active: str = "blue"  # "blue" or "green"
    deployment_history: List[Dict[str, Any]] = field(default_factory=list)
    rollback_timeout: int = 600  # 10 minutes
    health_check_interval: int = 30  # seconds

    def get_active_environment(self) -> DeploymentEnvironment:
        """Get the currently active environment."""
        return self.blue_env if self.current_active == "blue" else self.green_env

    def get_inactive_environment(self) -> DeploymentEnvironment:
        """Get the currently inactive environment."""
        return self.green_env if self.current_active == "blue" else self.blue_env

    def switch_traffic(self, target_env: str) -> bool:
        """Switch traffic to the specified environment."""
        if target_env not in ["blue", "green"]:
            logger.error(f"Invalid target environment: {target_env}")
            return False

        target = self.blue_env if target_env == "blue" else self.green_env

        if not target.is_healthy():
            logger.error(f"Cannot switch to {target_env}: environment is not healthy")
            return False

        try:
            # Update traffic weights
            self._update_traffic_weights(target_env, 100)
            self._update_traffic_weights(self.current_active, 0)

            # Update status
            target.status = "active"
            self.get_active_environment().status = "inactive"
            self.current_active = target_env

            # Log deployment event
            self._log_deployment_event("traffic_switch", target_env, "success")

            logger.info(f"Successfully switched traffic to {target_env}")
            return True

        except Exception as e:
            logger.error(f"Failed to switch traffic to {target_env}: {e}")
            self._log_deployment_event("traffic_switch", target_env, "failed", str(e))
            return False

    def deploy_to_inactive(self, version: str, image_tag: str) -> bool:
        """Deploy new version to the inactive environment."""
        inactive_env = self.get_inactive_environment()
        inactive_name = "green" if self.current_active == "blue" else "blue"

        logger.info(f"Starting deployment of version {version} to {inactive_name} environment")

        try:
            # Update environment metadata
            inactive_env.version = version
            inactive_env.status = "deploying"
            inactive_env.deployed_at = datetime.now()

            # Perform the deployment
            success = self._perform_deployment(inactive_name, image_tag)

            if success:
                inactive_env.status = "ready"
                self._log_deployment_event("deployment", inactive_name, "success", version)
                logger.info(f"Successfully deployed version {version} to {inactive_name}")
                return True
            else:
                inactive_env.status = "failed"
                self._log_deployment_event("deployment", inactive_name, "failed", version)
                logger.error(f"Failed to deploy version {version} to {inactive_name}")
                return False

        except Exception as e:
            inactive_env.status = "failed"
            logger.error(f"Deployment error: {e}")
            self._log_deployment_event("deployment", inactive_name, "error", version, str(e))
            return False

    def validate_deployment(self, environment: str) -> bool:
        """Validate that a deployment is working correctly."""
        env = self.blue_env if environment == "blue" else self.green_env

        if not env.health_url:
            logger.error(f"No health URL configured for {environment}")
            return False

        try:
            # Perform comprehensive health checks
            health_checks = [
                self._check_http_health(env.health_url),
                self._check_application_health(env.health_url),
                self._check_database_connectivity(),
                self._check_external_dependencies()
            ]

            if all(health_checks):
                env.health_status = "healthy"
                env.last_health_check = datetime.now()
                logger.info(f"{environment} environment passed all health checks")
                return True
            else:
                env.health_status = "unhealthy"
                logger.warning(f"{environment} environment failed health checks")
                return False

        except Exception as e:
            env.health_status = "unhealthy"
            logger.error(f"Health check failed for {environment}: {e}")
            return False

    def rollback(self) -> bool:
        """Rollback to the previously active environment."""
        if self.current_active == "blue":
            target_env = "green"
        else:
            target_env = "blue"

        logger.warning(f"Initiating rollback to {target_env} environment")

        # Check if target environment is still healthy
        if not self.validate_deployment(target_env):
            logger.error(f"Cannot rollback: {target_env} environment is not healthy")
            return False

        # Switch traffic back
        success = self.switch_traffic(target_env)

        if success:
            logger.info("Rollback completed successfully")
            self._log_deployment_event("rollback", target_env, "success")
        else:
            logger.error("Rollback failed")
            self._log_deployment_event("rollback", target_env, "failed")

        return success

    def _perform_deployment(self, environment: str, image_tag: str) -> bool:
        """Perform the actual deployment to the specified environment."""
        try:
            if os.getenv("DEPLOYMENT_PLATFORM") == "kubernetes":
                return self._deploy_kubernetes(environment, image_tag)
            elif os.getenv("DEPLOYMENT_PLATFORM") == "docker":
                return self._deploy_docker(environment, image_tag)
            else:
                # Default to docker-compose
                return self._deploy_docker_compose(environment, image_tag)

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return False

    def _deploy_kubernetes(self, environment: str, image_tag: str) -> bool:
        """Deploy to Kubernetes using kubectl."""
        try:
            # Update the deployment image
            cmd = [
                "kubectl", "set", "image",
                f"deployment/repo-scanner-{environment}",
                f"repo-scanner={image_tag}"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error(f"Kubernetes deployment failed: {result.stderr}")
                return False

            # Wait for rollout to complete
            cmd = [
                "kubectl", "rollout", "status",
                f"deployment/repo-scanner-{environment}",
                "--timeout=300s"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=320)

            if result.returncode != 0:
                logger.error(f"Kubernetes rollout failed: {result.stderr}")
                return False

            logger.info(f"Kubernetes deployment to {environment} completed")
            return True

        except subprocess.TimeoutExpired:
            logger.error("Kubernetes deployment timed out")
            return False
        except Exception as e:
            logger.error(f"Kubernetes deployment error: {e}")
            return False

    def _deploy_docker(self, environment: str, image_tag: str) -> bool:
        """Deploy using Docker."""
        try:
            # Stop old container
            subprocess.run(["docker", "stop", f"repo-scanner-{environment}"],
                         capture_output=True, timeout=60)

            # Remove old container
            subprocess.run(["docker", "rm", f"repo-scanner-{environment}"],
                         capture_output=True, timeout=60)

            # Start new container
            cmd = [
                "docker", "run", "-d",
                "--name", f"repo-scanner-{environment}",
                "--env-file", f".env.{environment}",
                "-p", f"808{1 if environment == 'blue' else 2}:8080",
                image_tag
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.error(f"Docker deployment failed: {result.stderr}")
                return False

            logger.info(f"Docker deployment to {environment} completed")
            return True

        except subprocess.TimeoutExpired:
            logger.error("Docker deployment timed out")
            return False
        except Exception as e:
            logger.error(f"Docker deployment error: {e}")
            return False

    def _deploy_docker_compose(self, environment: str, image_tag: str) -> bool:
        """Deploy using Docker Compose."""
        try:
            # Set environment variable for the image tag
            env = os.environ.copy()
            env[f"IMAGE_TAG_{environment.upper()}"] = image_tag

            # Deploy to specific environment
            cmd = ["docker-compose", "--profile", environment, "up", "-d", "--build"]

            result = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=300, env=env)

            if result.returncode != 0:
                logger.error(f"Docker Compose deployment failed: {result.stderr}")
                return False

            logger.info(f"Docker Compose deployment to {environment} completed")
            return True

        except subprocess.TimeoutExpired:
            logger.error("Docker Compose deployment timed out")
            return False
        except Exception as e:
            logger.error(f"Docker Compose deployment error: {e}")
            return False

    def _update_traffic_weights(self, environment: str, weight: int):
        """Update traffic weights for load balancer."""
        # This would integrate with your load balancer (nginx, istio, etc.)
        # For now, we'll simulate this
        env = self.blue_env if environment == "blue" else self.green_env
        env.traffic_weight = weight

        logger.info(f"Updated {environment} traffic weight to {weight}%")

    def _check_http_health(self, health_url: str) -> bool:
        """Check basic HTTP health."""
        try:
            response = requests.get(health_url, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def _check_application_health(self, base_url: str) -> bool:
        """Check application-specific health endpoints."""
        try:
            # Check main health endpoint
            response = requests.get(f"{base_url}/health", timeout=10)
            if response.status_code != 200:
                return False

            health_data = response.json()

            # Check that required services are healthy
            required_services = ["analysis_engine", "database", "cache"]
            for service in required_services:
                if not health_data.get("services", {}).get(service, False):
                    return False

            return True

        except Exception:
            return False

    def _check_database_connectivity(self) -> bool:
        """Check database connectivity."""
        # This would check actual database connection
        # For now, return True as a placeholder
        return True

    def _check_external_dependencies(self) -> bool:
        """Check external dependencies."""
        # This would check external APIs, services, etc.
        # For now, return True as a placeholder
        return True

    def _log_deployment_event(self, event_type: str, environment: str,
                            status: str, version: str = "", error: str = ""):
        """Log a deployment event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "environment": environment,
            "status": status,
            "version": version,
            "error": error
        }

        self.deployment_history.append(event)

        # Keep only last 100 events
        if len(self.deployment_history) > 100:
            self.deployment_history = self.deployment_history[-100:]

    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status."""
        return {
            "current_active": self.current_active,
            "blue": {
                "version": self.blue_env.version,
                "status": self.blue_env.status,
                "health": self.blue_env.health_status,
                "traffic_weight": self.blue_env.traffic_weight,
                "deployed_at": self.blue_env.deployed_at.isoformat() if self.blue_env.deployed_at else None
            },
            "green": {
                "version": self.green_env.version,
                "status": self.green_env.status,
                "health": self.green_env.health_status,
                "traffic_weight": self.green_env.traffic_weight,
                "deployed_at": self.green_env.deployed_at.isoformat() if self.green_env.deployed_at else None
            },
            "last_deployment_events": self.deployment_history[-5:] if self.deployment_history else []
        }


class BlueGreenManager:
    """High-level manager for blue-green deployments."""

    def __init__(self):
        self.deployment = BlueGreenDeployment(
            blue_env=DeploymentEnvironment(
                name="blue",
                version="",
                health_url=os.getenv("BLUE_HEALTH_URL", "http://blue-scanner:8080")
            ),
            green_env=DeploymentEnvironment(
                name="green",
                version="",
                health_url=os.getenv("GREEN_HEALTH_URL", "http://green-scanner:8080")
            )
        )

    def deploy_version(self, version: str, image_tag: str) -> bool:
        """Deploy a new version using blue-green strategy."""
        logger.info(f"Starting blue-green deployment of version {version}")

        # Deploy to inactive environment
        inactive_env = "green" if self.deployment.current_active == "blue" else "blue"

        if not self.deployment.deploy_to_inactive(version, image_tag):
            logger.error("Deployment failed")
            return False

        # Validate the deployment
        if not self.deployment.validate_deployment(inactive_env):
            logger.error("Deployment validation failed")
            return False

        # Switch traffic to new environment
        if not self.deployment.switch_traffic(inactive_env):
            logger.error("Traffic switch failed, initiating rollback")
            self.deployment.rollback()
            return False

        logger.info(f"Blue-green deployment of version {version} completed successfully")
        return True

    def emergency_rollback(self) -> bool:
        """Perform emergency rollback to previous version."""
        logger.warning("Initiating emergency rollback")
        return self.deployment.rollback()

    def get_status(self) -> Dict[str, Any]:
        """Get current deployment status."""
        return self.deployment.get_deployment_status()


# Global manager instance
_blue_green_manager = None

def get_blue_green_manager() -> BlueGreenManager:
    """Get the global blue-green deployment manager."""
    global _blue_green_manager
    if _blue_green_manager is None:
        _blue_green_manager = BlueGreenManager()
    return _blue_green_manager


def initialize_blue_green_deployment():
    """Initialize blue-green deployment system."""
    manager = get_blue_green_manager()

    # Set initial state - assume blue is active
    manager.deployment.blue_env.status = "active"
    manager.deployment.blue_env.traffic_weight = 100
    manager.deployment.green_env.status = "inactive"
    manager.deployment.green_env.traffic_weight = 0

    logger.info("Blue-green deployment system initialized")


if __name__ == "__main__":
    # Example usage
    initialize_blue_green_deployment()

    manager = get_blue_green_manager()

    # Deploy new version
    success = manager.deploy_version("v2.1.0", "repo-scanner:v2.1.0")

    if success:
        print("Deployment successful!")
    else:
        print("Deployment failed!")

    # Get status
    status = manager.get_status()
    print(f"Current active environment: {status['current_active']}")