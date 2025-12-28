#!/bin/bash
# Coverage Validation Script
# Ensures minimum code coverage requirements are met

set -e

echo "📊 Validating Code Coverage Requirements..."
echo "   Note: Initial minimums set - will be increased to 95% line, 90% branch over time"

# Run tests with coverage if not already run
if [ ! -f coverage.xml ]; then
    echo "Running tests with coverage..."
    pytest tests/ --tb=short -q --maxfail=1 --cov=src --cov-report=xml --cov-report=html > /dev/null 2>&1
fi

# Check if coverage.xml exists
if [ ! -f coverage.xml ]; then
    echo "❌ COVERAGE ERROR: coverage.xml not found"
    echo "💡 Run tests with coverage first: pytest tests/ --cov=src --cov-report=xml"
    exit 1
fi

# Parse coverage results
line_coverage=$(python -c "
import xml.etree.ElementTree as ET
tree = ET.parse('coverage.xml')
root = tree.getroot()
line_rate = float(root.attrib.get('line-rate', 0))
print(f'{line_rate:.1%}')
")

branch_coverage=$(python -c "
import xml.etree.ElementTree as ET
tree = ET.parse('coverage.xml')
root = tree.getroot()
branch_rate = float(root.attrib.get('branch-rate', 0))
print(f'{branch_rate:.1%}')
")

echo "📈 Coverage Results:"
echo "   Line Coverage: $line_coverage"
echo "   Branch Coverage: $branch_coverage"

# Check minimum requirements (initial targets - will be increased over time)
line_min="60.0%"  # Target: 95.0%
branch_min="0.0%"   # Target: 90.0%

line_pass=$(python -c "
line_cov = float('$line_coverage'.rstrip('%'))
line_min = float('$line_min'.rstrip('%'))
print('true' if line_cov >= line_min else 'false')
")

branch_pass=$(python -c "
branch_cov = float('$branch_coverage'.rstrip('%'))
branch_min = float('$branch_min'.rstrip('%'))
print('true' if branch_cov >= branch_min else 'false')
")

if [ "$line_pass" = "false" ]; then
    echo "❌ COVERAGE REQUIREMENT FAILED: Line coverage $line_coverage < $line_min"
    echo "💡 Improve test coverage by adding more tests"
    echo ""
    echo "Coverage Report: file://$(pwd)/htmlcov/index.html"
    exit 1
fi

if [ "$branch_pass" = "false" ]; then
    echo "❌ COVERAGE REQUIREMENT FAILED: Branch coverage $branch_coverage < $branch_min"
    echo "💡 Improve branch coverage by testing conditional logic"
    echo ""
    echo "Coverage Report: file://$(pwd)/htmlcov/index.html"
    exit 1
fi

echo "✅ INITIAL COVERAGE REQUIREMENTS MET"
echo "📊 Line: $line_coverage ≥ $line_min ✓ (Target: 95.0%)"
echo "📊 Branch: $branch_coverage ≥ $branch_min ✓ (Target: 90.0%)"
echo "🚀 Coverage standards established - continue improving toward targets"