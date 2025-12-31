#!/usr/bin/env python3
"""
Pipeline Profiling Module

Provides comprehensive profiling and bottleneck identification for the analysis pipeline
using cProfile and performance analysis tools.
"""

import cProfile
import pstats
import io
import time
import logging
from functools import wraps
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import psutil
import threading
from dataclasses import dataclass, field
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class ProfilingResult:
    """Result of a profiling operation."""
    function_name: str
    total_time: float
    call_count: int
    per_call_time: float
    cumulative_time: float
    memory_usage_mb: float
    timestamp: float

@dataclass
class PipelineProfile:
    """Profile of an entire pipeline run."""
    total_time: float
    memory_peak_mb: float
    stage_profiles: Dict[str, ProfilingResult] = field(default_factory=dict)
    bottlenecks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

class PipelineProfiler:
    """Profiler for analysis pipeline stages."""

    def __init__(self):
        self.profiles: Dict[str, ProfilingResult] = {}
        self.memory_monitor = psutil.Process()
        self._lock = threading.Lock()

    @contextmanager
    def profile_stage(self, stage_name: str):
        """Context manager to profile a pipeline stage."""
        profiler = cProfile.Profile()
        start_time = time.time()
        start_memory = self.memory_monitor.memory_info().rss / 1024 / 1024

        profiler.enable()

        try:
            yield
        finally:
            profiler.disable()
            end_time = time.time()
            end_memory = self.memory_monitor.memory_info().rss / 1024 / 1024

            # Get profiling stats
            stats_stream = io.StringIO()
            ps = pstats.Stats(profiler, stream=stats_stream)
            ps.sort_stats('cumulative')
            ps.print_stats()

            # Parse the stats to extract key metrics
            stats_output = stats_stream.getvalue()
            result = self._parse_profile_stats(stats_output, stage_name, end_time - start_time, end_memory - start_memory)

            with self._lock:
                self.profiles[stage_name] = result

            logger.info(f"Profiled stage '{stage_name}': {result.total_time:.3f}s, {result.memory_usage_mb:.1f}MB")

    def profile_function(self, func: Callable) -> Callable:
        """Decorator to profile a function."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            stage_name = f"{func.__module__}.{func.__name__}"
            with self.profile_stage(stage_name):
                return func(*args, **kwargs)
        return wrapper

    def _parse_profile_stats(self, stats_output: str, stage_name: str, total_time: float, memory_delta: float) -> ProfilingResult:
        """Parse cProfile output to extract key metrics."""
        lines = stats_output.split('\n')

        # Find the main function stats (usually the first non-header line)
        for line in lines:
            if line.strip() and not line.startswith(' '):
                # Parse the stats line
                # Format: ncalls  tottime  percall  cumtime  percall filename:lineno(function)
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        call_count = int(parts[0].split('/')[0])  # Handle ncalls like "1/1"
                        cumulative_time = float(parts[3])
                        per_call_time = cumulative_time / call_count if call_count > 0 else 0
                        break
                    except (ValueError, IndexError):
                        continue
                else:
                    continue
        else:
            # Fallback if parsing fails
            call_count = 1
            cumulative_time = total_time
            per_call_time = total_time

        return ProfilingResult(
            function_name=stage_name,
            total_time=total_time,
            call_count=call_count,
            per_call_time=per_call_time,
            cumulative_time=cumulative_time,
            memory_usage_mb=memory_delta,
            timestamp=time.time()
        )

    def get_pipeline_profile(self) -> PipelineProfile:
        """Generate a comprehensive pipeline profile."""
        if not self.profiles:
            return PipelineProfile(total_time=0.0, memory_peak_mb=0.0)

        total_time = sum(profile.total_time for profile in self.profiles.values())
        memory_peak = max((profile.memory_usage_mb for profile in self.profiles.values()), default=0.0)

        # Identify bottlenecks (stages taking >20% of total time)
        bottlenecks = []
        for name, profile in self.profiles.items():
            if profile.total_time > total_time * 0.2:
                bottlenecks.append(f"{name}: {profile.total_time:.3f}s ({profile.total_time/total_time*100:.1f}%)")

        # Generate recommendations
        recommendations = self._generate_recommendations()

        return PipelineProfile(
            total_time=total_time,
            memory_peak_mb=memory_peak,
            stage_profiles=self.profiles.copy(),
            bottlenecks=bottlenecks,
            recommendations=recommendations
        )

    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on profiling data."""
        recommendations = []

        if not self.profiles:
            return recommendations

        total_time = sum(p.total_time for p in self.profiles.values())

        # Check for memory-intensive stages
        memory_intensive = [name for name, profile in self.profiles.items() if profile.memory_usage_mb > 50]
        if memory_intensive:
            recommendations.append(f"Consider lazy loading for memory-intensive stages: {', '.join(memory_intensive)}")

        # Check for slow stages
        slow_stages = [name for name, profile in self.profiles.items() if profile.total_time > total_time * 0.3]
        if slow_stages:
            recommendations.append(f"Optimize slow stages: {', '.join(slow_stages)}")

        # Check for stages with high call counts
        high_call_stages = [name for name, profile in self.profiles.items() if profile.call_count > 1000]
        if high_call_stages:
            recommendations.append(f"Consider caching for frequently called functions: {', '.join(high_call_stages)}")

        # General recommendations
        if total_time > 30:
            recommendations.append("Consider parallelizing independent analysis stages")
        if any(p.memory_usage_mb > 100 for p in self.profiles.values()):
            recommendations.append("Implement memory optimization and garbage collection")
        if len(self.profiles) > 10:
            recommendations.append("Consider implementing lazy loading for optional analysis stages")

        return recommendations

    def save_profile_report(self, output_path: Path) -> Path:
        """Save a detailed profiling report."""
        profile = self.get_pipeline_profile()

        report_lines = [
            "# Pipeline Profiling Report",
            f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- **Total Time:** {profile.total_time:.3f}s",
            f"- **Peak Memory:** {profile.memory_peak_mb:.1f}MB",
            f"- **Stages Profiled:** {len(profile.stage_profiles)}",
            "",
            "## Stage Details",
            "",
            "| Stage | Time (s) | Memory (MB) | Calls | Time/Call (ms) | % of Total |",
            "|-------|----------|-------------|-------|----------------|------------|",
        ]

        for name, stage_profile in sorted(profile.stage_profiles.items(), key=lambda x: x[1].total_time, reverse=True):
            percentage = (stage_profile.total_time / profile.total_time * 100) if profile.total_time > 0 else 0
            time_per_call_ms = stage_profile.per_call_time * 1000
            report_lines.append(
                f"| {name} | {stage_profile.total_time:.3f} | {stage_profile.memory_usage_mb:.1f} | "
                f"{stage_profile.call_count} | {time_per_call_ms:.2f} | {percentage:.1f}% |"
            )

        report_lines.extend([
            "",
            "## Bottlenecks",
        ])

        if profile.bottlenecks:
            for bottleneck in profile.bottlenecks:
                report_lines.append(f"- {bottleneck}")
        else:
            report_lines.append("- No significant bottlenecks detected")

        report_lines.extend([
            "",
            "## Recommendations",
        ])

        if profile.recommendations:
            for rec in profile.recommendations:
                report_lines.append(f"- {rec}")
        else:
            report_lines.append("- No specific recommendations")

        report_content = "\n".join(report_lines)

        with open(output_path, 'w') as f:
            f.write(report_content)

        logger.info(f"Saved profiling report to {output_path}")
        return output_path

# Global profiler instance
_profiler = None

def get_pipeline_profiler() -> PipelineProfiler:
    """Get the global pipeline profiler instance."""
    global _profiler
    if _profiler is None:
        _profiler = PipelineProfiler()
    return _profiler

# Convenience functions
def profile_stage(stage_name: str):
    """Convenience context manager for profiling stages."""
    return get_pipeline_profiler().profile_stage(stage_name)

def profile_function(func: Callable) -> Callable:
    """Convenience decorator for profiling functions."""
    return get_pipeline_profiler().profile_function(func)
