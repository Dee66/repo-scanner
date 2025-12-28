#!/bin/bash
# A/B Testing Integration for CI/CD
# Integrates A/B testing with continuous validation pipeline

set -e

echo "🧪 Running A/B Testing Integration..."

EXPERIMENTS_DIR="experiments"
REPORTS_DIR="validation_data/ab_testing_reports"

# Create directories
mkdir -p "$EXPERIMENTS_DIR"
mkdir -p "$REPORTS_DIR"

# Check if there are any running experiments
RUNNING_EXPERIMENTS=$(ls -1 "$EXPERIMENTS_DIR"/*.json 2>/dev/null | xargs grep -l '"status": "running"' 2>/dev/null || true)

if [ -n "$RUNNING_EXPERIMENTS" ]; then
    echo "🏃 Found running experiments, checking status..."
    for exp_file in $RUNNING_EXPERIMENTS; do
        exp_id=$(basename "$exp_file" .json)
        echo "📊 Checking experiment: $exp_id"

        # Run experiment completion check
        if python3 scripts/run_ab_experiment.py report "$exp_id" | grep -q "completed"; then
            echo "✅ Experiment $exp_id completed"
        else
            echo "⏳ Experiment $exp_id still running"
        fi
    done
fi

# Generate A/B testing summary report
echo "📋 Generating A/B testing summary..."

REPORT_FILE="$REPORTS_DIR/ab_testing_summary_$(date +%Y%m%d_%H%M%S).md"

cat > "$REPORT_FILE" << 'EOF'
# A/B Testing Summary Report
**Generated:** $(date)

## Overview
This report summarizes the current state of A/B testing experiments for analysis improvements.

## Active Experiments
EOF

# List all experiments
if python3 scripts/run_ab_experiment.py list > /dev/null 2>&1; then
    python3 scripts/run_ab_experiment.py list >> "$REPORT_FILE"
else
    echo "📭 No experiments found" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << 'EOF'

## Recent Results
EOF

# Check for completed experiments in the last 24 hours
RECENT_COMPLETED=$(find "$EXPERIMENTS_DIR" -name "*.json" -mtime -1 -exec grep -l '"status": "completed"' {} \; 2>/dev/null || true)

if [ -n "$RECENT_COMPLETED" ]; then
    echo "### Completed Experiments (Last 24h)" >> "$REPORT_FILE"
    for exp_file in $RECENT_COMPLETED; do
        exp_id=$(basename "$exp_file" .json)
        echo "#### Experiment: $exp_id" >> "$REPORT_FILE"
        python3 scripts/run_ab_experiment.py report "$exp_id" | grep -E "(Description|Status|Results)" >> "$REPORT_FILE" 2>/dev/null || echo "Report generation failed" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    done
else
    echo "No recently completed experiments" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << 'EOF'

## Recommendations
- Run A/B experiments regularly to validate analysis improvements
- Focus on experiments that test specific hypotheses about effectiveness improvements
- Use statistical significance to guide decisions about adopting changes

EOF

echo "✅ A/B testing summary generated: $REPORT_FILE"

# Check for any critical findings
if [ -n "$RECENT_COMPLETED" ]; then
    echo "🔍 Analyzing recent experiment results..."

    # Check if any experiments show significant improvements
    for exp_file in $RECENT_COMPLETED; do
        exp_id=$(basename "$exp_file" .json)
        if python3 scripts/run_ab_experiment.py report "$exp_id" 2>/dev/null | grep -q "Statistically significant improvement"; then
            echo "🎯 SIGNIFICANT IMPROVEMENT DETECTED in experiment $exp_id"
            echo "💡 Consider implementing the winning variant in production"
        fi
    done
fi

echo "✅ A/B Testing Integration Complete"