#!/usr/bin/env python3
"""
Automated Effectiveness Monitoring System for Repository Intelligence Scanner
Tracks and validates the ongoing effectiveness of the 99.999% uptime implementation
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import aiohttp
import psutil
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EffectivenessMonitor:
    """Automated monitoring system for 99.999% uptime effectiveness"""

    def __init__(self, config_path: str = "monitoring/effectiveness_config.yml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.metrics_history: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []

    def _load_config(self) -> Dict[str, Any]:
        """Load monitoring configuration"""
        if not self.config_path.exists():
            # Create default configuration
            default_config = {
                "monitoring": {
                    "interval_seconds": 60,
                    "retention_days": 30,
                    "uptime_threshold": 99.999,
                    "alert_thresholds": {
                        "response_time_ms": 2000,
                        "error_rate_percent": 0.001,
                        "cpu_usage_percent": 80,
                        "memory_usage_percent": 85
                    }
                },
                "endpoints": {
                    "health_check": "http://localhost:8080/health",
                    "metrics": "http://localhost:8080/metrics",
                    "api_status": "http://localhost:8080/api/v1/status"
                },
                "alerting": {
                    "email_enabled": False,
                    "slack_enabled": False,
                    "pagerduty_enabled": False
                }
            }
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)
            return default_config

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    async def check_endpoint_health(self, url: str, timeout: float = 5.0) -> Dict[str, Any]:
        """Check health of a specific endpoint"""
        start_time = time.time()
        result = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "response_time_ms": None,
            "status_code": None,
            "healthy": False,
            "error": None
        }

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    result["status_code"] = response.status
                    result["response_time_ms"] = (time.time() - start_time) * 1000
                    result["healthy"] = response.status == 200

                    if response.status != 200:
                        result["error"] = f"HTTP {response.status}"

        except asyncio.TimeoutError:
            result["error"] = "Timeout"
            result["response_time_ms"] = timeout * 1000
        except Exception as e:
            result["error"] = str(e)
            result["response_time_ms"] = (time.time() - start_time) * 1000

        return result

    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level performance metrics"""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "network_connections": len(psutil.net_connections()),
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }

    def calculate_uptime_metrics(self, health_checks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate uptime and reliability metrics"""
        if not health_checks:
            return {}

        total_checks = len(health_checks)
        successful_checks = sum(1 for check in health_checks if check.get("healthy", False))
        uptime_percentage = (successful_checks / total_checks) * 100

        response_times = [check["response_time_ms"] for check in health_checks if check["response_time_ms"] is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None

        return {
            "total_checks": total_checks,
            "successful_checks": successful_checks,
            "uptime_percentage": uptime_percentage,
            "average_response_time_ms": avg_response_time,
            "min_response_time_ms": min(response_times) if response_times else None,
            "max_response_time_ms": max(response_times) if response_times else None,
            "time_window_minutes": len(health_checks)  # Assuming 1 check per minute
        }

    def check_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for alert conditions based on configured thresholds"""
        alerts = []
        thresholds = self.config["monitoring"]["alert_thresholds"]

        # Uptime alert
        if metrics.get("uptime_percentage", 100) < self.config["monitoring"]["uptime_threshold"]:
            alerts.append({
                "type": "uptime_breach",
                "severity": "critical",
                "message": f"Uptime {metrics['uptime_percentage']:.3f}% below threshold {self.config['monitoring']['uptime_threshold']}%",
                "timestamp": datetime.now().isoformat()
            })

        # Response time alert
        if metrics.get("average_response_time_ms", 0) > thresholds["response_time_ms"]:
            alerts.append({
                "type": "response_time_high",
                "severity": "warning",
                "message": f"Average response time {metrics['average_response_time_ms']:.1f}ms exceeds threshold {thresholds['response_time_ms']}ms",
                "timestamp": datetime.now().isoformat()
            })

        # System resource alerts
        system_metrics = metrics.get("system_metrics", {})
        if system_metrics.get("cpu_percent", 0) > thresholds["cpu_usage_percent"]:
            alerts.append({
                "type": "high_cpu_usage",
                "severity": "warning",
                "message": f"CPU usage {system_metrics['cpu_percent']:.1f}% exceeds threshold {thresholds['cpu_usage_percent']}%",
                "timestamp": datetime.now().isoformat()
            })

        if system_metrics.get("memory_percent", 0) > thresholds["memory_usage_percent"]:
            alerts.append({
                "type": "high_memory_usage",
                "severity": "warning",
                "message": f"Memory usage {system_metrics['memory_percent']:.1f}% exceeds threshold {thresholds['memory_usage_percent']}%",
                "timestamp": datetime.now().isoformat()
            })

        return alerts

    async def perform_monitoring_cycle(self) -> Dict[str, Any]:
        """Perform a complete monitoring cycle"""
        logger.info("Starting monitoring cycle")

        # Check all configured endpoints
        endpoints = self.config["endpoints"]
        health_checks = []

        for endpoint_name, url in endpoints.items():
            logger.debug(f"Checking endpoint: {endpoint_name} ({url})")
            health_check = await self.check_endpoint_health(url)
            health_checks.append(health_check)

        # Collect system metrics
        system_metrics = self.collect_system_metrics()

        # Calculate uptime metrics
        uptime_metrics = self.calculate_uptime_metrics(health_checks)

        # Combine all metrics
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "health_checks": health_checks,
            "system_metrics": system_metrics,
            **uptime_metrics
        }

        # Check for alerts
        alerts = self.check_alerts(metrics)
        if alerts:
            logger.warning(f"Generated {len(alerts)} alerts")
            for alert in alerts:
                logger.warning(f"Alert: {alert['message']}")

        # Store metrics history
        self.metrics_history.append(metrics)
        self.alerts.extend(alerts)

        # Clean up old metrics (retention policy)
        cutoff_date = datetime.now() - timedelta(days=self.config["monitoring"]["retention_days"])
        self.metrics_history = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"]) > cutoff_date
        ]

        logger.info(f"Monitoring cycle completed. Uptime: {uptime_metrics.get('uptime_percentage', 0):.3f}%")
        return metrics

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive effectiveness report"""
        if not self.metrics_history:
            return {"error": "No metrics data available"}

        # Calculate overall statistics
        all_checks = []
        for metrics in self.metrics_history[-100:]:  # Last 100 cycles
            all_checks.extend(metrics.get("health_checks", []))

        overall_uptime = self.calculate_uptime_metrics(all_checks)

        # Alert summary
        alert_summary = {}
        for alert in self.alerts[-100:]:  # Last 100 alerts
            alert_type = alert["type"]
            alert_summary[alert_type] = alert_summary.get(alert_type, 0) + 1

        # Trend analysis
        recent_metrics = self.metrics_history[-10:]  # Last 10 cycles
        uptime_trend = [m.get("uptime_percentage", 100) for m in recent_metrics]
        response_time_trend = [m.get("average_response_time_ms", 0) for m in recent_metrics]

        report = {
            "generated_at": datetime.now().isoformat(),
            "monitoring_period_days": self.config["monitoring"]["retention_days"],
            "overall_uptime": overall_uptime,
            "alert_summary": alert_summary,
            "trends": {
                "uptime_last_10_cycles": uptime_trend,
                "response_time_last_10_cycles": response_time_trend
            },
            "effectiveness_assessment": self._assess_effectiveness(overall_uptime),
            "recommendations": self._generate_recommendations(overall_uptime, alert_summary)
        }

        return report

    def _assess_effectiveness(self, uptime_metrics: Dict[str, Any]) -> str:
        """Assess overall effectiveness of the 99.999% uptime implementation"""
        uptime = uptime_metrics.get("uptime_percentage", 0)
        avg_response_time = uptime_metrics.get("average_response_time_ms", 0)

        if uptime >= 99.999 and avg_response_time <= 1000:
            return "EXCELLENT: Meeting or exceeding all 99.999% uptime requirements"
        elif uptime >= 99.99 and avg_response_time <= 2000:
            return "GOOD: Close to 99.999% uptime target with acceptable performance"
        elif uptime >= 99.9:
            return "FAIR: Basic uptime requirements met, but not 99.999% target"
        else:
            return "POOR: Significant uptime and performance issues detected"

    def _generate_recommendations(self, uptime_metrics: Dict[str, Any], alert_summary: Dict[str, int]) -> List[str]:
        """Generate recommendations based on monitoring data"""
        recommendations = []

        uptime = uptime_metrics.get("uptime_percentage", 0)
        avg_response_time = uptime_metrics.get("average_response_time_ms", 0)

        if uptime < 99.999:
            recommendations.append("Implement additional redundancy measures to achieve 99.999% uptime")
            recommendations.append("Review and optimize error handling and recovery procedures")

        if avg_response_time > 2000:
            recommendations.append("Optimize application performance to reduce response times")
            recommendations.append("Consider implementing response time caching or optimization")

        if alert_summary.get("high_cpu_usage", 0) > 5:
            recommendations.append("Monitor and optimize CPU-intensive operations")
            recommendations.append("Consider horizontal scaling for high CPU usage periods")

        if alert_summary.get("high_memory_usage", 0) > 5:
            recommendations.append("Investigate memory leaks and optimize memory usage")
            recommendations.append("Implement memory monitoring and alerting thresholds")

        if not recommendations:
            recommendations.append("Continue monitoring - system performing within acceptable parameters")

        return recommendations

    async def run_continuous_monitoring(self):
        """Run continuous monitoring loop"""
        logger.info("Starting continuous effectiveness monitoring")

        while True:
            try:
                await self.perform_monitoring_cycle()

                # Generate periodic reports
                if len(self.metrics_history) % 60 == 0:  # Every hour
                    report = self.generate_report()
                    self._save_report(report)

                await asyncio.sleep(self.config["monitoring"]["interval_seconds"])

            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    def _save_report(self, report: Dict[str, Any]):
        """Save monitoring report to file"""
        report_path = Path("monitoring/effectiveness_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Effectiveness report saved to {report_path}")

async def main():
    """Main function for running the effectiveness monitor"""
    monitor = EffectivenessMonitor()

    # Run a single monitoring cycle for testing
    logger.info("Running single monitoring cycle for testing...")
    metrics = await monitor.perform_monitoring_cycle()

    print("\nMonitoring Results:")
    print(f"Uptime: {metrics.get('uptime_percentage', 0):.3f}%")
    print(f"Average Response Time: {metrics.get('average_response_time_ms', 0):.1f}ms")

    # Generate and display report
    report = monitor.generate_report()
    print(f"\nEffectiveness Assessment: {report.get('effectiveness_assessment', 'Unknown')}")

    print("\nRecommendations:")
    for rec in report.get('recommendations', []):
        print(f"- {rec}")

    # Save report
    monitor._save_report(report)

    # Uncomment to run continuous monitoring
    # await monitor.run_continuous_monitoring()

if __name__ == "__main__":
    asyncio.run(main())