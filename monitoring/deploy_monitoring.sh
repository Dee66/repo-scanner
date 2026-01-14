#!/bin/bash
# Monitoring Setup Script for Repository Intelligence Scanner
# Deploys Prometheus, Alertmanager, Grafana, and monitoring infrastructure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
MONITORING_NAMESPACE="${MONITORING_NAMESPACE:-monitoring}"
PROMETHEUS_VERSION="${PROMETHEUS_VERSION:-v2.40.0}"
ALERTMANAGER_VERSION="${ALERTMANAGER_VERSION:-v0.24.0}"
GRAFANA_VERSION="${GRAFANA_VERSION:-9.3.0}"

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

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi

    if ! command -v helm &> /dev/null; then
        log_error "helm not found. Please install Helm."
        exit 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Unable to connect to Kubernetes cluster."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Function to create monitoring namespace
create_namespace() {
    log_info "Creating monitoring namespace..."

    kubectl create namespace "$MONITORING_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

    log_success "Monitoring namespace created"
}

# Function to deploy Prometheus
deploy_prometheus() {
    log_info "Deploying Prometheus..."

    # Create ConfigMap for Prometheus configuration
    kubectl create configmap prometheus-config \
        --from-file=prometheus.yml="$SCRIPT_DIR/prometheus.yml" \
        --from-file=alert_rules.yml="$SCRIPT_DIR/alert_rules.yml" \
        --namespace="$MONITORING_NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    # Deploy Prometheus using Helm
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update

    cat <<EOF | helm upgrade --install prometheus prometheus-community/prometheus \
        --namespace "$MONITORING_NAMESPACE" \
        --values -
server:
  configMapOverrideName: prometheus-config
  retention: 30d
  resources:
    requests:
      memory: 1Gi
      cpu: 500m
    limits:
      memory: 2Gi
      cpu: 1000m
alertmanager:
  enabled: false  # We'll deploy Alertmanager separately
nodeExporter:
  enabled: true
pushgateway:
  enabled: false
EOF

    log_success "Prometheus deployed"
}

# Function to deploy Alertmanager
deploy_alertmanager() {
    log_info "Deploying Alertmanager..."

    # Create ConfigMap for Alertmanager configuration
    kubectl create configmap alertmanager-config \
        --from-file=alertmanager.yml="$SCRIPT_DIR/alertmanager.yml" \
        --namespace="$MONITORING_NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    # Deploy Alertmanager using Helm
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update

    cat <<EOF | helm upgrade --install alertmanager prometheus-community/alertmanager \
        --namespace "$MONITORING_NAMESPACE" \
        --values -
configMapOverrideName: alertmanager-config
resources:
  requests:
    memory: 512Mi
    cpu: 250m
  limits:
    memory: 1Gi
    cpu: 500m
EOF

    log_success "Alertmanager deployed"
}

# Function to deploy Grafana
deploy_grafana() {
    log_info "Deploying Grafana..."

    # Create ConfigMap for Grafana provisioning
    kubectl create configmap grafana-provisioning \
        --from-file=grafana-provisioning.yml="$SCRIPT_DIR/grafana-provisioning.yml" \
        --namespace="$MONITORING_NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    # Create ConfigMap for dashboard
    kubectl create configmap repo-scanner-dashboard \
        --from-file=repo-scanner-overview.json="$SCRIPT_DIR/repo-scanner-overview-dashboard.json" \
        --namespace="$MONITORING_NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -

    # Deploy Grafana using Helm
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update

    cat <<EOF | helm upgrade --install grafana grafana/grafana \
        --namespace "$MONITORING_NAMESPACE" \
        --values -
adminPassword: admin123  # Change this in production!
datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-server
      access: proxy
      isDefault: true
dashboardProviders:
  dashboardproviders.yaml:
    apiVersion: 1
    providers:
    - name: 'repo-scanner'
      type: file
      disableDeletion: false
      updateIntervalSeconds: 10
      allowUiUpdates: true
      options:
        path: /var/lib/grafana/dashboards/repo-scanner
dashboards:
  repo-scanner:
    repo-scanner-overview:
      file: repo-scanner-dashboard/repo-scanner-overview.json
dashboardConfigMaps:
  repo-scanner: repo-scanner-dashboard
resources:
  requests:
    memory: 512Mi
    cpu: 250m
  limits:
    memory: 1Gi
    cpu: 500m
EOF

    log_success "Grafana deployed"
}

# Function to deploy monitoring for repo-scanner
deploy_repo_scanner_monitoring() {
    log_info "Deploying Repository Scanner monitoring..."

    # Create ServiceMonitor for Prometheus
    cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: repo-scanner-monitor
  namespace: $MONITORING_NAMESPACE
spec:
  selector:
    matchLabels:
      app: repo-scanner
  endpoints:
  - port: http
    path: /metrics
    interval: 15s
EOF

    # Create PrometheusRule for alerts
    cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: repo-scanner-alerts
  namespace: $MONITORING_NAMESPACE
spec:
  groups:
  - name: repo_scanner_alerts
    rules:
    - alert: RepoScannerDown
      expr: up{job="repo-scanner-api"} == 0
      for: 5m
      labels:
        severity: critical
        service: repo-scanner
      annotations:
        summary: "Repository Intelligence Scanner API is down"
        description: "Repository Intelligence Scanner API has been down for more than 5 minutes."
EOF

    log_success "Repository Scanner monitoring deployed"
}

# Function to wait for deployments
wait_for_deployments() {
    log_info "Waiting for deployments to be ready..."

    # Wait for Prometheus
    kubectl wait --for=condition=available --timeout=300s deployment/prometheus-server -n "$MONITORING_NAMESPACE"

    # Wait for Alertmanager
    kubectl wait --for=condition=available --timeout=300s deployment/alertmanager -n "$MONITORING_NAMESPACE"

    # Wait for Grafana
    kubectl wait --for=condition=available --timeout=300s deployment/grafana -n "$MONITORING_NAMESPACE"

    log_success "All monitoring components are ready"
}

# Function to display access information
display_access_info() {
    log_info "Monitoring stack deployment completed!"
    echo ""
    echo "Access Information:"
    echo "=================="

    # Prometheus
    PROMETHEUS_PORT=$(kubectl get svc prometheus-server -n "$MONITORING_NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}')
    echo "Prometheus: http://localhost:$PROMETHEUS_PORT"

    # Alertmanager
    ALERTMANAGER_PORT=$(kubectl get svc alertmanager -n "$MONITORING_NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}')
    echo "Alertmanager: http://localhost:$ALERTMANAGER_PORT"

    # Grafana
    GRAFANA_PORT=$(kubectl get svc grafana -n "$MONITORING_NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}')
    echo "Grafana: http://localhost:$GRAFANA_PORT"
    echo "  Username: admin"
    echo "  Password: admin123 (CHANGE THIS!)"
    echo ""

    echo "Next Steps:"
    echo "1. Update Grafana password"
    echo "2. Configure alert notification channels in Alertmanager"
    echo "3. Import additional dashboards as needed"
    echo "4. Set up backup and retention policies"
}

# Main deployment logic
log_info "🚀 Starting monitoring stack deployment"

check_prerequisites
create_namespace
deploy_prometheus
deploy_alertmanager
deploy_grafana
deploy_repo_scanner_monitoring
wait_for_deployments
display_access_info

log_success "🎉 Monitoring stack deployment completed successfully!"