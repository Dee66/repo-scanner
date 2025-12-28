#!/bin/bash
# Validation Data Management CI/CD Integration
# Automates data management tasks in CI/CD pipeline

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_MANAGEMENT_SCRIPT="$SCRIPT_DIR/../scripts/data_management.py"

echo "🔧 Starting Validation Data Management CI/CD Integration"

# Function to run data management command
run_data_cmd() {
    local cmd="$1"
    echo "📋 Running: python3 $DATA_MANAGEMENT_SCRIPT $cmd"
    python3 "$DATA_MANAGEMENT_SCRIPT" $cmd
}

# Function to check if we should run maintenance
should_run_maintenance() {
    # Run maintenance daily or when explicitly requested
    local force_maintenance="${FORCE_MAINTENANCE:-false}"
    local last_maintenance_file="$PROJECT_ROOT/.last_maintenance"

    if [[ "$force_maintenance" == "true" ]]; then
        echo "✅ Forced maintenance requested"
        return 0
    fi

    if [[ ! -f "$last_maintenance_file" ]]; then
        echo "✅ No previous maintenance record found"
        return 0
    fi

    local last_run=$(cat "$last_maintenance_file")
    local current_time=$(date +%s)
    local time_diff=$((current_time - last_run))
    local day_seconds=$((24 * 60 * 60))

    if [[ $time_diff -gt $day_seconds ]]; then
        echo "✅ Daily maintenance due (last run: $(date -d "@$last_run"))"
        return 0
    else
        echo "⏭️  Maintenance not due yet"
        return 1
    fi
}

# Function to update maintenance timestamp
update_maintenance_timestamp() {
    date +%s > "$PROJECT_ROOT/.last_maintenance"
}

# Main CI/CD workflow
main() {
    cd "$PROJECT_ROOT"

    echo "🔍 Step 1: Verify data integrity"
    if ! run_data_cmd "verify"; then
        echo "❌ Data integrity check failed"
        exit 1
    fi

    echo "📊 Step 2: Check data quality"
    run_data_cmd "quality"

    echo "📋 Step 3: Generate data report"
    run_data_cmd "report --output-file ci_data_report_$(date +%Y%m%d_%H%M%S).json"

    echo "🔧 Step 4: Check if maintenance should run"
    if should_run_maintenance; then
        echo "🔧 Running maintenance tasks..."

        # Update repository data
        echo "📥 Updating repository data..."
        if run_data_cmd "update"; then
            echo "✅ Repository data updated"
        else
            echo "⚠️  Repository data update failed, continuing..."
        fi

        # Run maintenance cycle
        echo "🔧 Running maintenance cycle..."
        run_data_cmd "maintenance"

        # Monitor quality
        echo "📊 Monitoring data quality..."
        run_data_cmd "monitor"

        # Create backup
        echo "💾 Creating data backup..."
        run_data_cmd "backup"

        # Update maintenance timestamp
        update_maintenance_timestamp
        echo "✅ Maintenance completed"
    else
        echo "⏭️  Skipping maintenance tasks"
    fi

    # Create version if there were changes
    if [[ "${CREATE_VERSION:-false}" == "true" ]]; then
        echo "🏷️  Creating new data version..."
        local changes_file="${CHANGES_FILE:-}"
        local metadata_file="${METADATA_FILE:-}"

        local cmd="create-version --description \"CI/CD automated version\" --author \"CI/CD Pipeline\""

        if [[ -n "$changes_file" && -f "$changes_file" ]]; then
            cmd="$cmd --changes $(cat "$changes_file" | tr '\n' ' ')"
        fi

        if [[ -n "$metadata_file" && -f "$metadata_file" ]]; then
            cmd="$cmd --metadata $metadata_file"
        fi

        run_data_cmd "$cmd"
        echo "✅ New version created"
    fi

    echo "🎉 Validation Data Management CI/CD Integration completed successfully"
}

# Run main function
main "$@"