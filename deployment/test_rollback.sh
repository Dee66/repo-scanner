#!/bin/bash
# Rollback Testing Script for Repository Intelligence Scanner
# Tests rollback procedures under various failure scenarios

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
DEPLOYMENT_PLATFORM="${DEPLOYMENT_PLATFORM:-docker-compose}"
TEST_VERSION="${TEST_VERSION:-test-rollback}"
FAILURE_SCENARIO="${1:-health_check_failure}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

cd "$PROJECT_ROOT"

log_info "🧪 Starting Rollback Testing"
log_info "📦 Test Version: $TEST_VERSION"
log_info "🏗️  Platform: $DEPLOYMENT_PLATFORM"
log_info "💥 Failure Scenario: $FAILURE_SCENARIO"

# Setup test environment
setup_test_env() {
    log_info "🔧 Setting up test environment"

    # Build test image
    docker build -t "repo-scanner:$TEST_VERSION" \
                 --build-arg FAILURE_SCENARIO="$FAILURE_SCENARIO" \
                 -f Dockerfile.test .

    # Ensure clean state
    docker-compose --profile blue down || true
    docker-compose --profile green down || true

    # Start with blue environment active
    export IMAGE_TAG_BLUE="repo-scanner:latest"
    export IMAGE_TAG_GREEN="repo-scanner:$TEST_VERSION"

    log_info "🚀 Starting blue environment (stable version)"
    docker-compose --profile blue up -d

    # Wait for blue to be healthy
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "http://localhost:8080/health" >/dev/null 2>&1; then
            log_success "Blue environment is healthy"
            break
        fi
        log_info "Waiting for blue environment to be healthy (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "Blue environment failed to become healthy"
        exit 1
    fi
}

# Test different failure scenarios
test_health_check_failure() {
    log_info "💥 Testing: Health Check Failure Scenario"

    # Deploy failing version to green
    log_info "📦 Deploying failing version to green environment"
    docker-compose --profile green up -d

    # Wait a bit then check if green fails health checks
    sleep 30

    if curl -f -s "http://localhost:8081/health" >/dev/null 2>&1; then
        log_error "Green environment should have failed health checks but didn't"
        return 1
    fi

    log_success "Green environment correctly failed health checks"

    # Test that blue is still active
    if curl -f -s "http://localhost:8080/health" >/dev/null 2>&1; then
        log_success "Blue environment remained active during green failure"
    else
        log_error "Blue environment became unavailable"
        return 1
    fi

    return 0
}

test_startup_failure() {
    log_info "💥 Testing: Startup Failure Scenario"

    # Create a version that fails to start
    docker build -t "repo-scanner:startup-fail" \
                 --build-arg STARTUP_FAILURE=true \
                 -f Dockerfile.test .

    export IMAGE_TAG_GREEN="repo-scanner:startup-fail"

    log_info "📦 Attempting to deploy startup-failing version to green"
    if docker-compose --profile green up -d; then
        # Wait to see if it actually starts
        sleep 30
        if docker-compose --profile green ps | grep -q "Up"; then
            log_error "Container should have failed to start but appears to be running"
            docker-compose --profile green down
            return 1
        else
            log_success "Container correctly failed to start"
        fi
    else
        log_success "Deployment correctly failed during startup"
    fi

    return 0
}

test_runtime_failure() {
    log_info "💥 Testing: Runtime Failure Scenario"

    # Deploy a version that fails after some time
    docker build -t "repo-scanner:runtime-fail" \
                 --build-arg RUNTIME_FAILURE=true \
                 -f Dockerfile.test .

    export IMAGE_TAG_GREEN="repo-scanner:runtime-fail"

    log_info "📦 Deploying runtime-failing version to green"
    docker-compose --profile green up -d

    # Wait for it to start and pass initial health checks
    sleep 20

    if ! curl -f -s "http://localhost:8081/health" >/dev/null 2>&1; then
        log_error "Green environment failed initial health check"
        return 1
    fi

    log_info "🟢 Green environment initially healthy, waiting for runtime failure"

    # Wait for runtime failure (container should exit)
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if ! docker-compose --profile green ps | grep -q "Up"; then
            log_success "Green environment correctly failed at runtime"
            break
        fi
        sleep 10
        ((attempt++))
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "Green environment should have failed but remained running"
        docker-compose --profile green down
        return 1
    fi

    return 0
}

test_traffic_switch_failure() {
    log_info "💥 Testing: Traffic Switch Failure Scenario"

    # Deploy healthy version to green
    export IMAGE_TAG_GREEN="repo-scanner:latest"
    docker-compose --profile green up -d

    # Wait for green to be healthy
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "http://localhost:8081/health" >/dev/null 2>&1; then
            log_success "Green environment is healthy"
            break
        fi
        sleep 10
        ((attempt++))
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "Green environment failed to become healthy"
        return 1
    fi

    # Simulate traffic switch failure (in real scenario, this would be a LB config failure)
    log_info "🔄 Simulating traffic switch to green"

    # In a real scenario, we'd test that if the traffic switch fails,
    # the system automatically rolls back. For this test, we'll verify
    # that both environments remain accessible during the transition.

    if curl -f -s "http://localhost:8080/health" >/dev/null 2>&1 && \
       curl -f -s "http://localhost:8081/health" >/dev/null 2>&1; then
        log_success "Both environments remain accessible during transition"
    else
        log_error "One or both environments became unavailable during transition"
        return 1
    fi

    return 0
}

test_manual_rollback() {
    log_info "🔄 Testing: Manual Rollback Procedure"

    # Assume green is active (from previous test)
    log_info "🔄 Switching traffic back to blue (rollback)"

    # Verify blue is still healthy
    if ! curl -f -s "http://localhost:8080/health" >/dev/null 2>&1; then
        log_error "Blue environment is not healthy for rollback"
        return 1
    fi

    # Stop green environment
    docker-compose --profile green down

    # Verify blue is still working
    if curl -f -s "http://localhost:8080/health" >/dev/null 2>&1; then
        log_success "Manual rollback successful - blue environment active"
    else
        log_error "Manual rollback failed - blue environment not accessible"
        return 1
    fi

    return 0
}

# Cleanup function
cleanup() {
    log_info "🧹 Cleaning up test environment"
    docker-compose --profile blue down || true
    docker-compose --profile green down || true

    # Remove test images
    docker rmi "repo-scanner:$TEST_VERSION" || true
    docker rmi "repo-scanner:startup-fail" || true
    docker rmi "repo-scanner:runtime-fail" || true
}

# Main test execution
trap cleanup EXIT

setup_test_env

# Run the specified test scenario
case "$FAILURE_SCENARIO" in
    "health_check_failure")
        if test_health_check_failure; then
            log_success "✅ Health check failure test PASSED"
        else
            log_error "❌ Health check failure test FAILED"
            exit 1
        fi
        ;;

    "startup_failure")
        if test_startup_failure; then
            log_success "✅ Startup failure test PASSED"
        else
            log_error "❌ Startup failure test FAILED"
            exit 1
        fi
        ;;

    "runtime_failure")
        if test_runtime_failure; then
            log_success "✅ Runtime failure test PASSED"
        else
            log_error "❌ Runtime failure test FAILED"
            exit 1
        fi
        ;;

    "traffic_switch_failure")
        if test_traffic_switch_failure; then
            log_success "✅ Traffic switch failure test PASSED"
        else
            log_error "❌ Traffic switch failure test FAILED"
            exit 1
        fi
        ;;

    "manual_rollback")
        if test_manual_rollback; then
            log_success "✅ Manual rollback test PASSED"
        else
            log_error "❌ Manual rollback test FAILED"
            exit 1
        fi
        ;;

    "all")
        log_info "🧪 Running all rollback tests"

        local all_passed=true

        if ! test_health_check_failure; then all_passed=false; fi
        if ! test_startup_failure; then all_passed=false; fi
        if ! test_runtime_failure; then all_passed=false; fi
        if ! test_traffic_switch_failure; then all_passed=false; fi
        if ! test_manual_rollback; then all_passed=false; fi

        if $all_passed; then
            log_success "✅ All rollback tests PASSED"
        else
            log_error "❌ Some rollback tests FAILED"
            exit 1
        fi
        ;;

    *)
        log_error "Unknown failure scenario: $FAILURE_SCENARIO"
        log_info "Available scenarios: health_check_failure, startup_failure, runtime_failure, traffic_switch_failure, manual_rollback, all"
        exit 1
        ;;
esac

log_success "🎉 Rollback testing completed successfully!"