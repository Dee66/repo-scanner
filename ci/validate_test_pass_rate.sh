#!/bin/bash
# Test Pass Requirement Validator
# Ensures 100% test pass rate for all merges

set -e

echo "🔍 Validating 100% Test Pass Requirement..."

# Run tests and capture results
echo "Running test suite..."
pytest tests/ --tb=short -q --maxfail=1 > test_results.log 2>&1
test_exit_code=$?

# Parse results from final summary line
summary_line=$(grep -E "[0-9]+ (passed|failed|skipped|xfailed)" test_results.log | tail -1)
passed_tests=$(echo "$summary_line" | grep -oE "[0-9]+ passed" | awk '{print $1}' || echo "0")
failed_tests=$(echo "$summary_line" | grep -oE "[0-9]+ failed" | awk '{print $1}' || echo "0")
skipped_tests=$(echo "$summary_line" | grep -oE "[0-9]+ skipped" | awk '{print $1}' || echo "0")
xfailed_tests=$(echo "$summary_line" | grep -oE "[0-9]+ xfailed" | awk '{print $1}' || echo "0")

# Default empty values to 0
failed_tests=${failed_tests:-0}
skipped_tests=${skipped_tests:-0}
xfailed_tests=${xfailed_tests:-0}

# Calculate total tests
total_tests=$((passed_tests + failed_tests + skipped_tests + xfailed_tests))

# Calculate effective passed (passed + xfailed)
effective_passed=$((passed_tests + xfailed_tests))

echo "📊 Test Results:"
echo "   Total tests: $total_tests"
echo "   Passed: $passed_tests"
echo "   Failed: $failed_tests"
echo "   Skipped: $skipped_tests"
echo "   XFailed: $xfailed_tests"
echo "   Effective Pass Rate: $effective_passed/$total_tests"

# Validate requirements: No actual failures allowed
if [ "$failed_tests" -gt 0 ]; then
    echo "❌ TEST VALIDATION FAILED: $failed_tests tests failed"
    echo "💡 All tests must pass before merge"
    echo ""
    echo "Failed tests:"
    grep -A 5 -B 1 "FAILED\|ERROR" test_results.log || true
    exit 1
fi

# Calculate effective pass rate (passed + xfailed as successful outcomes)
effective_passed=$((passed_tests + xfailed_tests))
actual_tested=$((passed_tests + failed_tests + xfailed_tests))

if [ "$actual_tested" -gt 0 ]; then
    pass_percentage=$(( (effective_passed * 100) / actual_tested ))
    echo "📈 Pass Rate: $pass_percentage% ($effective_passed/$actual_tested tests successful, excluding $skipped_tests skipped)"
fi

if [ "$skipped_tests" -gt 0 ] || [ "$xfailed_tests" -gt 0 ]; then
    echo "⚠️  INFO: $skipped_tests tests skipped, $xfailed_tests tests expected to fail"
    if [ "$skipped_tests" -gt 0 ]; then
        echo "   Skipped tests may indicate incomplete implementation"
        echo "   Consider implementing or removing skipped tests"
    fi
    if [ "$xfailed_tests" -gt 0 ]; then
        echo "   XFailed tests are expected failures (marked with @pytest.mark.xfail)"
        echo "   These represent known limitations or incomplete features"
    fi
fi

echo "✅ 100% TEST PASS REQUIREMENT VALIDATED"
echo "🚀 Code is ready for merge"

# Clean up
rm -f test_results.log