"""Advanced reporting and analytics infrastructure for comprehensive test insights."""

import pytest
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Use absolute path based on conftest.py location
_conf_dir = Path(__file__).parent

# Advanced reporting configuration
_advanced_reports_dir = _conf_dir / ".pytest_cache" / "advanced_reports"
_analytics_data_file = _conf_dir / ".pytest_cache" / "analytics_data.json"
_trend_analysis_file = _conf_dir / ".pytest_cache" / "trend_analysis.json"

# Analytics configuration
ANALYTICS_CONFIG = {
    "trend_window_days": 30,
    "performance_percentiles": [50, 75, 90, 95, 99],
    "risk_thresholds": {
        "flakiness_rate": 0.15,
        "failure_rate": 0.10,
        "performance_regression": 0.20
    },
    "report_formats": ["html", "json", "csv", "png"],
    "dashboard_refresh_interval": 3600  # 1 hour
}


def load_analytics_data() -> Dict[str, Any]:
    """Load analytics data from cache file."""
    if _analytics_data_file.exists():
        try:
            with open(_analytics_data_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "test_runs": [],
        "performance_metrics": [],
        "coverage_trends": [],
        "flakiness_history": [],
        "last_updated": None
    }


def save_analytics_data(data: Dict[str, Any]):
    """Save analytics data to cache file."""
    _advanced_reports_dir.mkdir(parents=True, exist_ok=True)
    with open(_analytics_data_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def load_trend_analysis() -> Dict[str, Any]:
    """Load trend analysis data."""
    if _trend_analysis_file.exists():
        try:
            with open(_trend_analysis_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_trend_analysis(data: Dict[str, Any]):
    """Save trend analysis data."""
    _advanced_reports_dir.mkdir(parents=True, exist_ok=True)
    with open(_trend_analysis_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)


class AdvancedReporter:
    """Advanced reporting and analytics engine."""

    def __init__(self):
        self.analytics_data = load_analytics_data()
        self.trend_data = load_trend_analysis()

    def collect_test_run_data(self, session_results: Dict[str, Any], performance_data: List[Dict], coverage_data: Dict[str, Any]):
        """Collect comprehensive test run data for analytics."""
        run_data = {
            "timestamp": datetime.now().isoformat(),
            "session_id": f"run_{int(datetime.now().timestamp())}",
            "test_results": session_results,
            "performance_metrics": performance_data,
            "coverage_data": coverage_data,
            "environment": {
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                "platform": os.sys.platform,
                "pytest_version": pytest.__version__
            }
        }

        # Add to analytics data
        self.analytics_data["test_runs"].append(run_data)
        self.analytics_data["performance_metrics"].extend(performance_data)
        self.analytics_data["coverage_trends"].append({
            "timestamp": run_data["timestamp"],
            "coverage": coverage_data
        })
        self.analytics_data["last_updated"] = run_data["timestamp"]

        # Keep only last 100 runs for performance
        self.analytics_data["test_runs"] = self.analytics_data["test_runs"][-100:]
        self.analytics_data["performance_metrics"] = self.analytics_data["performance_metrics"][-1000:]

        save_analytics_data(self.analytics_data)

    def generate_trend_analysis(self) -> Dict[str, Any]:
        """Generate comprehensive trend analysis."""
        if not self.analytics_data["test_runs"]:
            return {}

        # Analyze test result trends
        test_runs = self.analytics_data["test_runs"][-30:]  # Last 30 runs
        trends = self._analyze_test_trends(test_runs)

        # Analyze performance trends
        performance_trends = self._analyze_performance_trends()

        # Analyze coverage trends
        coverage_trends = self._analyze_coverage_trends()

        # Risk assessment
        risk_assessment = self._assess_risks(trends, performance_trends, coverage_trends)

        trend_analysis = {
            "analysis_timestamp": datetime.now().isoformat(),
            "time_window": f"{len(test_runs)} test runs",
            "test_trends": trends,
            "performance_trends": performance_trends,
            "coverage_trends": coverage_trends,
            "risk_assessment": risk_assessment,
            "recommendations": self._generate_recommendations(risk_assessment)
        }

        save_trend_analysis(trend_analysis)
        return trend_analysis

    def _analyze_test_trends(self, test_runs: List[Dict]) -> Dict[str, Any]:
        """Analyze test result trends."""
        if not test_runs:
            return {}

        # Extract metrics over time
        timestamps = []
        pass_rates = []
        failure_rates = []
        durations = []

        for run in test_runs:
            results = run.get("test_results", {})
            total = results.get("total_tests", 0)
            passed = results.get("passed", 0)
            failed = results.get("failed", 0)

            if total > 0:
                timestamps.append(run["timestamp"])
                pass_rates.append(passed / total)
                failure_rates.append(failed / total)
                durations.append(results.get("duration", 0))

        # Calculate trends
        trends = {
            "pass_rate_trend": self._calculate_trend(pass_rates),
            "failure_rate_trend": self._calculate_trend(failure_rates),
            "duration_trend": self._calculate_trend(durations),
            "stability_score": self._calculate_stability_score(pass_rates),
            "recent_performance": {
                "avg_pass_rate": sum(pass_rates[-5:]) / len(pass_rates[-5:]) if len(pass_rates) >= 5 else 0,
                "avg_failure_rate": sum(failure_rates[-5:]) / len(failure_rates[-5:]) if len(failure_rates) >= 5 else 0,
                "avg_duration": sum(durations[-5:]) / len(durations[-5:]) if len(durations) >= 5 else 0
            }
        }

        return trends

    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends."""
        performance_data = self.analytics_data.get("performance_metrics", [])
        if not performance_data:
            return {}

        # Group by test ID
        test_performance = defaultdict(list)
        for metric in performance_data:
            test_id = metric.get("test_id", "unknown")
            test_performance[test_id].append(metric)

        trends = {}
        for test_id, metrics in test_performance.items():
            durations = [m.get("duration", 0) for m in metrics]
            if len(durations) >= 3:
                if HAS_PANDAS:
                    avg_duration = np.mean(durations)
                    percentiles = {p: np.percentile(durations, p) for p in ANALYTICS_CONFIG["performance_percentiles"]}
                else:
                    avg_duration = sum(durations) / len(durations)
                    sorted_durations = sorted(durations)
                    percentiles = {}
                    for p in ANALYTICS_CONFIG["performance_percentiles"]:
                        idx = int((p / 100) * (len(sorted_durations) - 1))
                        percentiles[p] = sorted_durations[idx]

                trends[test_id] = {
                    "avg_duration": avg_duration,
                    "duration_trend": self._calculate_trend(durations),
                    "percentiles": percentiles,
                    "regression_alert": self._detect_performance_regression(durations)
                }

        return trends

    def _analyze_coverage_trends(self) -> Dict[str, Any]:
        """Analyze coverage trends."""
        coverage_trends = self.analytics_data.get("coverage_trends", [])
        if not coverage_trends:
            return {}

        # Extract coverage metrics over time
        overall_coverage = []
        timestamps = []

        for trend in coverage_trends[-20:]:  # Last 20 data points
            coverage = trend.get("coverage", {})
            overall = coverage.get("overall", 0)
            if overall > 0:
                overall_coverage.append(overall)
                timestamps.append(trend["timestamp"])

        trends = {
            "coverage_trend": self._calculate_trend(overall_coverage) if overall_coverage else "insufficient_data",
            "current_coverage": overall_coverage[-1] if overall_coverage else 0,
            "coverage_stability": self._calculate_stability_score(overall_coverage) if len(overall_coverage) >= 5 else 0
        }

        return trends

    def _assess_risks(self, test_trends: Dict, perf_trends: Dict, coverage_trends: Dict) -> Dict[str, Any]:
        """Assess overall risk levels."""
        risks = {
            "test_stability": "low",
            "performance": "low",
            "coverage": "low",
            "overall_risk": "low",
            "risk_factors": []
        }

        # Test stability risk
        if test_trends.get("stability_score", 1) < 0.8:
            risks["test_stability"] = "high"
            risks["risk_factors"].append("Low test stability score")

        failure_rate = test_trends.get("recent_performance", {}).get("avg_failure_rate", 0)
        if failure_rate > ANALYTICS_CONFIG["risk_thresholds"]["failure_rate"]:
            risks["test_stability"] = "medium"
            risks["risk_factors"].append(f"High failure rate: {failure_rate:.1%}")

        # Performance risk
        perf_regressions = sum(1 for trend in perf_trends.values() if trend.get("regression_alert"))
        if perf_regressions > len(perf_trends) * 0.3:  # 30% of tests have regressions
            risks["performance"] = "high"
            risks["risk_factors"].append(f"Performance regressions in {perf_regressions} tests")

        # Coverage risk
        current_coverage = coverage_trends.get("current_coverage", 100)
        if current_coverage < 80:
            risks["coverage"] = "high"
            risks["risk_factors"].append(f"Low coverage: {current_coverage:.1f}%")
        elif current_coverage < 90:
            risks["coverage"] = "medium"
            risks["risk_factors"].append(f"Moderate coverage: {current_coverage:.1f}%")

        # Overall risk
        risk_levels = [risks["test_stability"], risks["performance"], risks["coverage"]]
        if "high" in risk_levels:
            risks["overall_risk"] = "high"
        elif "medium" in risk_levels:
            risks["overall_risk"] = "medium"

        return risks

    def _generate_recommendations(self, risk_assessment: Dict) -> List[str]:
        """Generate actionable recommendations based on risk assessment."""
        recommendations = []

        if risk_assessment["test_stability"] in ["medium", "high"]:
            recommendations.extend([
                "Investigate flaky tests and implement quarantine measures",
                "Review test isolation and dependencies",
                "Consider parallel test execution optimization"
            ])

        if risk_assessment["performance"] in ["medium", "high"]:
            recommendations.extend([
                "Profile performance-critical tests",
                "Optimize test setup and teardown",
                "Review resource usage in test environment"
            ])

        if risk_assessment["coverage"] in ["medium", "high"]:
            recommendations.extend([
                "Add test coverage for uncovered modules",
                "Review test quality and assertion comprehensiveness",
                "Implement coverage gates in CI/CD pipeline"
            ])

        if risk_assessment["overall_risk"] == "high":
            recommendations.append("Immediate attention required - multiple risk factors detected")

        return recommendations

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a series of values."""
        if len(values) < 3:
            return "insufficient_data"

        if not HAS_PANDAS:
            # Simple trend calculation without numpy
            if len(values) >= 2:
                diff = values[-1] - values[0]
                if diff > 0.01:
                    return "improving"
                elif diff < -0.01:
                    return "declining"
                else:
                    return "stable"
            return "insufficient_data"

        # Simple linear trend
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]

        if slope > 0.01:
            return "improving"
        elif slope < -0.01:
            return "declining"
        else:
            return "stable"

    def _calculate_stability_score(self, values: List[float]) -> float:
        """Calculate stability score (0-1, higher is more stable)."""
        if len(values) < 3:
            return 0.0

        if not HAS_PANDAS:
            # Simple stability calculation
            mean_val = sum(values) / len(values)
            if mean_val == 0:
                return 1.0
            variance = sum((x - mean_val) ** 2 for x in values) / len(values)
            std_val = variance ** 0.5
            cv = std_val / mean_val
            stability = 1 / (1 + cv)
            return min(stability, 1.0)

        # Coefficient of variation (lower is more stable)
        mean_val = np.mean(values)
        if mean_val == 0:
            return 1.0  # Perfect stability if all values are 0

        std_val = np.std(values)
        cv = std_val / mean_val

        # Convert to stability score (inverse of coefficient of variation)
        stability = 1 / (1 + cv)
        return min(stability, 1.0)

    def _detect_performance_regression(self, durations: List[float]) -> bool:
        """Detect performance regression in test durations."""
        if len(durations) < 5:
            return False

        if not HAS_PANDAS:
            # Simple regression detection
            recent = durations[-3:]
            earlier = durations[:-3]
            recent_avg = sum(recent) / len(recent)
            earlier_avg = sum(earlier) / len(earlier)

            if earlier_avg == 0:
                return False

            regression_pct = (recent_avg - earlier_avg) / earlier_avg
            return bool(regression_pct > ANALYTICS_CONFIG["risk_thresholds"]["performance_regression"])

        recent_avg = np.mean(durations[-3:])  # Last 3 runs
        baseline_avg = np.mean(durations[:-3])  # Earlier runs

        if baseline_avg == 0:
            return False

        regression_pct = (recent_avg - baseline_avg) / baseline_avg
        return bool(regression_pct > ANALYTICS_CONFIG["risk_thresholds"]["performance_regression"])

    def generate_advanced_report(self, format_type: str = "html") -> str:
        """Generate advanced analytics report in specified format."""
        trend_analysis = self.generate_trend_analysis()

        if format_type == "html":
            return self._generate_html_report(trend_analysis)
        elif format_type == "json":
            return json.dumps(trend_analysis, indent=2)
        else:
            return json.dumps(trend_analysis, indent=2)

    def _generate_html_report(self, trend_analysis: Dict) -> str:
        """Generate HTML dashboard report."""
        # Extract data for template
        risk = trend_analysis.get("risk_assessment", {})
        test_trends = trend_analysis.get("test_trends", {})
        perf_trends = trend_analysis.get("performance_trends", {})
        coverage_trends = trend_analysis.get("coverage_trends", {})

        perf_regressions = sum(1 for t in perf_trends.values() if t.get("regression_alert"))
        recommendations_html = "\n".join(f"<li>{rec}</li>" for rec in trend_analysis.get("recommendations", []))

        # Use string replacement instead of format() to avoid CSS curly brace conflicts
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Advanced Test Analytics Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .metric-card {{ border: 1px solid #ddd; padding: 15px; margin: 10px; border-radius: 5px; }}
        .risk-high {{ background-color: #ffebee; border-color: #f44336; }}
        .risk-medium {{ background-color: #fff3e0; border-color: #ff9800; }}
        .risk-low {{ background-color: #e8f5e8; border-color: #4caf50; }}
        .trend-improving {{ color: #4caf50; }}
        .trend-declining {{ color: #f44336; }}
        .trend-stable {{ color: #ff9800; }}
        h1, h2 {{ color: #333; }}
        .recommendations {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>🚀 Advanced Test Analytics Dashboard</h1>
    <p><strong>Generated:</strong> {trend_analysis.get("analysis_timestamp", "Unknown")}</p>

    <h2>📊 Risk Assessment</h2>
    <div class="metric-card risk-{risk.get("overall_risk", "unknown")}">
        <h3>Overall Risk Level: {risk.get("overall_risk", "unknown").upper()}</h3>
        <p><strong>Risk Factors:</strong> {", ".join(risk.get("risk_factors", []))}</p>
    </div>

    <h2>🧪 Test Stability</h2>
    <div class="metric-card risk-{risk.get("test_stability", "unknown")}">
        <h3>Test Stability: {risk.get("test_stability", "unknown").upper()}</h3>
        <p><strong>Stability Score:</strong> {test_trends.get("stability_score", 0):.2f}</p>
        <p><strong>Pass Rate Trend:</strong> <span class="trend-{test_trends.get("pass_rate_trend", "unknown")}">{test_trends.get("pass_rate_trend", "unknown").upper()}</span></p>
        <p><strong>Avg Pass Rate (Recent):</strong> {test_trends.get("recent_performance", {}).get("avg_pass_rate", 0):.1%}</p>
    </div>

    <h2>⚡ Performance Trends</h2>
    <div class="metric-card risk-{risk.get("performance", "unknown")}">
        <h3>Performance Risk: {risk.get("performance", "unknown").upper()}</h3>
        <p><strong>Tests with Regressions:</strong> {perf_regressions}</p>
    </div>

    <h2>📈 Coverage Trends</h2>
    <div class="metric-card risk-{risk.get("coverage", "unknown")}">
        <h3>Coverage Risk: {risk.get("coverage", "unknown").upper()}</h3>
        <p><strong>Current Coverage:</strong> {coverage_trends.get("current_coverage", 0):.1f}%</p>
        <p><strong>Coverage Trend:</strong> <span class="trend-{coverage_trends.get("coverage_trend", "unknown")}">{coverage_trends.get("coverage_trend", "unknown").upper()}</span></p>
    </div>

    <h2>💡 Recommendations</h2>
    <div class="recommendations">
        <ul>
            {recommendations_html}
        </ul>
    </div>
</body>
</html>"""

        return html_content


def generate_advanced_analytics_report(format_type: str = "html") -> str:
    """Generate comprehensive advanced analytics report."""
    reporter = AdvancedReporter()
    return reporter.generate_advanced_report(format_type)


def run_advanced_analytics() -> Dict[str, Any]:
    """Run complete advanced analytics suite."""
    reporter = AdvancedReporter()

    # Generate trend analysis
    trend_analysis = reporter.generate_trend_analysis()

    # Generate reports in different formats
    reports = {}
    for fmt in ANALYTICS_CONFIG["report_formats"]:
        try:
            reports[fmt] = reporter.generate_advanced_report(fmt)
        except Exception as e:
            reports[fmt] = f"Error generating {fmt} report: {str(e)}"

    return {
        "trend_analysis": trend_analysis,
        "reports": reports,
        "analytics_timestamp": datetime.now().isoformat()
    }


# Integration with pytest session
def pytest_sessionfinish(session, exitstatus):
    """Generate advanced analytics report at session end if requested."""
    if session.config.getoption("--advanced-report"):
        print("\n📊 Generating Advanced Analytics Report...")

        try:
            analytics_results = run_advanced_analytics()

            # Save HTML report
            report_dir = _advanced_reports_dir
            report_dir.mkdir(parents=True, exist_ok=True)

            html_report_path = report_dir / "analytics_dashboard.html"
            with open(html_report_path, 'w') as f:
                f.write(analytics_results["reports"]["html"])

            json_report_path = report_dir / "analytics_data.json"
            with open(json_report_path, 'w') as f:
                json.dump(analytics_results, f, indent=2, default=str)

            terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
            if terminalreporter:
                terminalreporter.write_sep("=", "Advanced Analytics Report Generated")
                terminalreporter.write_line(f"HTML Dashboard: {html_report_path}")
                terminalreporter.write_line(f"JSON Data: {json_report_path}")

                risk = analytics_results["trend_analysis"].get("risk_assessment", {})
                terminalreporter.write_line(f"Overall Risk Level: {risk.get('overall_risk', 'unknown').upper()}")
                terminalreporter.write_line(f"Risk Factors: {len(risk.get('risk_factors', []))}")

                recommendations = analytics_results["trend_analysis"].get("recommendations", [])
                if recommendations:
                    terminalreporter.write_line("Top Recommendations:")
                    for rec in recommendations[:3]:
                        terminalreporter.write_line(f"  • {rec}")

                terminalreporter.write_line("")

        except Exception as e:
            print(f"Error generating advanced analytics report: {e}")


# Test functions for advanced reporting
def test_advanced_reporter_initialization():
    """Test that the advanced reporter can be initialized."""
    reporter = AdvancedReporter()
    assert reporter is not None
    assert isinstance(reporter.analytics_data, dict)


def test_trend_analysis_calculation():
    """Test trend analysis calculations."""
    reporter = AdvancedReporter()

    # Test with empty data
    trends = reporter._analyze_test_trends([])
    assert trends == {}

    # Test with sample data
    sample_runs = [
        {
            "timestamp": "2024-01-01T00:00:00",
            "test_results": {"total_tests": 100, "passed": 95, "failed": 5, "duration": 10.0}
        },
        {
            "timestamp": "2024-01-02T00:00:00",
            "test_results": {"total_tests": 100, "passed": 90, "failed": 10, "duration": 12.0}
        }
    ]

    trends = reporter._analyze_test_trends(sample_runs)
    assert "pass_rate_trend" in trends
    assert "stability_score" in trends
    assert "recent_performance" in trends


def test_risk_assessment():
    """Test risk assessment functionality."""
    reporter = AdvancedReporter()

    # Test low risk scenario
    test_trends = {"stability_score": 0.95, "recent_performance": {"avg_failure_rate": 0.02}}
    perf_trends = {}
    coverage_trends = {"current_coverage": 95.0}

    risk = reporter._assess_risks(test_trends, perf_trends, coverage_trends)
    assert risk["overall_risk"] == "low"

    # Test high risk scenario
    test_trends_high = {"stability_score": 0.5, "recent_performance": {"avg_failure_rate": 0.25}}
    coverage_trends_high = {"current_coverage": 60.0}

    risk_high = reporter._assess_risks(test_trends_high, perf_trends, coverage_trends_high)
    assert risk_high["overall_risk"] == "high"


def test_performance_regression_detection():
    """Test performance regression detection."""
    reporter = AdvancedReporter()

    # Test with improving performance (no regression)
    durations = [10.0, 9.5, 9.0, 8.8, 8.5]
    assert not reporter._detect_performance_regression(durations)

    # Test with regression
    durations_regression = [8.0, 8.1, 8.2, 12.0, 15.0]  # More significant regression
    regression_detected = reporter._detect_performance_regression(durations_regression)
    assert regression_detected is True


def test_stability_score_calculation():
    """Test stability score calculation."""
    reporter = AdvancedReporter()

    # Test stable data
    stable_values = [0.95, 0.96, 0.94, 0.95, 0.97]
    stability = reporter._calculate_stability_score(stable_values)
    assert stability > 0.8

    # Test unstable data
    unstable_values = [0.5, 0.9, 0.3, 0.95, 0.2]
    stability_unstable = reporter._calculate_stability_score(unstable_values)
    assert stability_unstable < stability


def test_trend_calculation():
    """Test trend calculation."""
    reporter = AdvancedReporter()

    # Test improving trend
    improving = [0.8, 0.85, 0.9, 0.92, 0.95]
    assert reporter._calculate_trend(improving) == "improving"

    # Test declining trend
    declining = [0.95, 0.9, 0.85, 0.8, 0.75]
    assert reporter._calculate_trend(declining) == "declining"

    # Test stable trend
    stable = [0.9, 0.91, 0.89, 0.9, 0.91]
    assert reporter._calculate_trend(stable) == "stable"


def test_advanced_report_generation():
    """Test advanced report generation."""
    # Test HTML report generation
    html_report = generate_advanced_analytics_report("html")
    assert "<!DOCTYPE html>" in html_report
    assert "Advanced Test Analytics Dashboard" in html_report

    # Test JSON report generation
    json_report = generate_advanced_analytics_report("json")
    assert isinstance(json_report, str)
    # Should be valid JSON
    parsed = json.loads(json_report)
    assert isinstance(parsed, dict)


def test_analytics_data_persistence():
    """Test analytics data saving and loading."""
    # Create test data
    test_data = {
        "test_runs": [{"session_id": "test_123", "timestamp": "2024-01-01T00:00:00"}],
        "performance_metrics": [{"test_id": "test_1", "duration": 1.5}],
        "coverage_trends": [{"timestamp": "2024-01-01T00:00:00", "coverage": {"overall": 85.0}}],
        "flakiness_history": [],
        "last_updated": "2024-01-01T00:00:00"
    }

    # Save data
    save_analytics_data(test_data)

    # Load data
    loaded_data = load_analytics_data()
    assert loaded_data["last_updated"] == "2024-01-01T00:00:00"
    assert len(loaded_data["test_runs"]) == 1


def test_run_advanced_analytics():
    """Test the main advanced analytics function."""
    results = run_advanced_analytics()
    assert isinstance(results, dict)
    assert "trend_analysis" in results
    assert "reports" in results
    assert "analytics_timestamp" in results

    # Check that all report formats are generated
    reports = results["reports"]
    for fmt in ANALYTICS_CONFIG["report_formats"]:
        assert fmt in reports