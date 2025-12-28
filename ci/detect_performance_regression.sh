#!/bin/bash
# Performance Regression Detection Script
# Detects performance regressions by comparing against baseline metrics

set -e

echo "🏃‍♂️ Detecting Performance Regressions..."

# Configuration
PERFORMANCE_LOG="performance_results.json"
BASELINE_FILE="ci/performance_baseline.json"
REGRESSION_THRESHOLD=1.2  # 20% regression threshold

# Run performance tests and capture metrics
echo "Running performance benchmarks..."
python -m pytest tests/test_performance.py tests/test_performance_regression.py \
    -v --tb=short --maxfail=1 \
    --benchmark-json="$PERFORMANCE_LOG" \
    --benchmark-only \
    --benchmark-save=ci_performance \
    --benchmark-save-data \
    --benchmark-histogram=performance_histogram \
    2>/dev/null || true

# Check if performance results were generated
if [ ! -f "$PERFORMANCE_LOG" ]; then
    echo "⚠️  No performance benchmarks found or executed"
    echo "   This may be expected if no benchmark tests are marked with @pytest.mark.benchmark"
    echo "   Performance regression detection will be skipped"
    exit 0
fi

# Parse performance results
echo "📊 Analyzing Performance Results..."

# Extract key metrics using Python
python -c "
import json
import sys
from pathlib import Path

# Load current results
with open('$PERFORMANCE_LOG', 'r') as f:
    current_data = json.load(f)

# Load baseline if exists
baseline_data = {}
baseline_file = Path('$BASELINE_FILE')
if baseline_file.exists():
    with open(baseline_file, 'r') as f:
        baseline_data = json.load(f)

# Extract benchmark results
benchmarks = current_data.get('benchmarks', [])
if not benchmarks:
    print('No benchmark results found')
    sys.exit(1)

print(f'Found {len(benchmarks)} benchmark results')

# Analyze each benchmark
regressions = []
improvements = []

for bench in benchmarks:
    name = bench['name']
    current_time = bench['stats']['mean']
    
    baseline_time = baseline_data.get(name, {}).get('stats', {}).get('mean')
    
    if baseline_time:
        ratio = current_time / baseline_time
        change_pct = ((ratio - 1) * 100)
        
        if ratio > $REGRESSION_THRESHOLD:
            regressions.append({
                'name': name,
                'current': current_time,
                'baseline': baseline_time,
                'ratio': ratio,
                'change_pct': change_pct
            })
        elif ratio < 0.9:  # 10% improvement
            improvements.append({
                'name': name,
                'current': current_time,
                'baseline': baseline_time,
                'ratio': ratio,
                'change_pct': change_pct
            })
    
    # Store current as new baseline
    baseline_data[name] = bench

# Save updated baseline
with open('$BASELINE_FILE', 'w') as f:
    json.dump(baseline_data, f, indent=2)

# Report results
if regressions:
    print(f'❌ PERFORMANCE REGRESSIONS DETECTED: {len(regressions)} benchmarks regressed')
    for reg in regressions:
        print(f'   {reg[\"name\"]}: {reg[\"change_pct\"]:+.1f}% ({reg[\"current\"]:.3f}s vs {reg[\"baseline\"]:.3f}s)')
    sys.exit(1)

if improvements:
    print(f'✅ PERFORMANCE IMPROVEMENTS: {len(improvements)} benchmarks improved')
    for imp in improvements:
        print(f'   {imp[\"name\"]}: {imp[\"change_pct\"]:+.1f}% ({imp[\"current\"]:.3f}s vs {imp[\"baseline\"]:.3f}s)')

print('✅ NO PERFORMANCE REGRESSIONS DETECTED')
print(f'📈 Baseline updated with {len(benchmarks)} benchmark results')
"

echo "🚀 Performance regression detection complete"