# Post-Deployment Monitoring and Validation Guide

## Overview

This guide provides comprehensive procedures for monitoring and validating the Repository Intelligence Scanner after production deployment. It ensures system stability, performance, and reliability through systematic validation and continuous monitoring.

## Immediate Post-Deployment Validation

### Phase 1: Deployment Verification (0-15 minutes)

#### Infrastructure Validation
```bash
# 1. Verify cluster resources
kubectl get nodes -o wide
kubectl get pods -n repo-scanner -o wide
kubectl get services -n repo-scanner
kubectl get ingress -n repo-scanner

# Expected: All pods running, services accessible, ingress configured

# 2. Check resource allocation
kubectl top nodes
kubectl top pods -n repo-scanner

# Expected: Resource usage within normal ranges (< 70% CPU/Memory)

# 3. Verify persistent volumes
kubectl get pvc -n repo-scanner
kubectl get pv

# Expected: All PVCs bound, PVs available
```

#### Application Validation
```bash
# 1. Health endpoint verification
curl -f -w "@curl-format.txt" https://scanner.yourcompany.com/health

# Expected: HTTP 200, response time < 2 seconds

# 2. API endpoint testing
curl -X GET https://scanner.yourcompany.com/api/v1/status \
  -H "Authorization: Bearer <service-token>"

# Expected: JSON response with status information

# 3. Database connectivity
kubectl exec -n repo-scanner deployment/repo-scanner -- \
  python -c "
import psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
conn.close()
print('Database connection successful')
"

# Expected: No connection errors
```

#### Security Validation
```bash
# 1. Network policy verification
kubectl get networkpolicies -n repo-scanner

# Expected: Policies applied and enforced

# 2. RBAC verification
kubectl auth can-i list pods --as=system:serviceaccount:repo-scanner:repo-scanner-sa

# Expected: Appropriate permissions granted

# 3. Security context verification
kubectl get pods -n repo-scanner -o jsonpath='{.items[*].spec.securityContext}'

# Expected: Security contexts properly configured
```

### Phase 2: Functional Testing (15-60 minutes)

#### API Functionality Tests
```bash
# 1. Repository scanning test
curl -X POST https://scanner.yourcompany.com/api/v1/scan \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <service-token>" \
  -d '{
    "repository_url": "https://github.com/test/repo",
    "scan_type": "full"
  }'

# Expected: Scan job created successfully

# 2. Results retrieval test
curl -X GET https://scanner.yourcompany.com/api/v1/results/{job_id} \
  -H "Authorization: Bearer <service-token>"

# Expected: Scan results returned

# 3. Authentication test
curl -X GET https://scanner.yourcompany.com/api/v1/status \
  -H "Authorization: Bearer invalid-token"

# Expected: HTTP 401 Unauthorized
```

#### Performance Baseline Testing
```bash
# 1. Load testing (using existing load test script)
python scripts/load_test.py \
  --url https://scanner.yourcompany.com \
  --concurrency 10 \
  --duration 300 \
  --token <service-token>

# Expected: < 5% error rate, response time < 3 seconds (95th percentile)

# 2. Memory leak testing
# Monitor memory usage over time
kubectl top pods -n repo-scanner --containers

# Expected: Stable memory usage, no continuous growth

# 3. Database performance
kubectl exec -n repo-scanner deployment/repo-scanner -- \
  python -c "
import time
start = time.time()
# Execute sample database operations
end = time.time()
print(f'DB operation time: {end - start:.3f}s')
"

# Expected: Query times within acceptable ranges
```

### Phase 3: Integration Testing (1-4 hours)

#### External System Integration
```bash
# 1. Monitoring integration verification
# Check Prometheus targets
curl http://prometheus.repo-scanner.svc.cluster.local:9090/api/v1/targets

# Expected: All targets healthy

# 2. Alert manager verification
curl http://alertmanager.repo-scanner.svc.cluster.local:9093/api/v2/alerts

# Expected: No unexpected alerts

# 3. Logging integration
# Verify logs are being collected
kubectl logs -n repo-scanner -l app=repo-scanner --tail=10

# Expected: Logs visible in ELK stack
```

#### Data Flow Validation
```bash
# 1. End-to-end scan workflow
# Submit scan -> Monitor progress -> Retrieve results
SCAN_ID=$(curl -X POST https://scanner.yourcompany.com/api/v1/scan \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <service-token>" \
  -d '{"repository_url": "https://github.com/test/repo"}' | jq -r '.scan_id')

# Monitor scan progress
while true; do
  STATUS=$(curl -X GET https://scanner.yourcompany.com/api/v1/scan/$SCAN_ID/status \
    -H "Authorization: Bearer <service-token>" | jq -r '.status')
  echo "Scan status: $STATUS"
  if [ "$STATUS" = "completed" ]; then break; fi
  sleep 30
done

# Retrieve results
curl -X GET https://scanner.yourcompany.com/api/v1/results/$SCAN_ID \
  -H "Authorization: Bearer <service-token>"

# Expected: Complete scan workflow successful
```

## Continuous Monitoring Setup

### Monitoring Dashboard Configuration

#### Grafana Dashboard Verification
```bash
# 1. Access Grafana dashboard
# URL: https://grafana.yourcompany.com/d/repo-scanner-main

# 2. Verify key metrics panels:
# - System Health: All green indicators
# - Performance: Response times within SLA
# - Resource Usage: Within capacity limits
# - Error Rates: Below threshold
# - Throughput: Meeting requirements

# 3. Configure alerts based on dashboard metrics
# - Response time > 5 seconds
# - Error rate > 5%
# - Memory usage > 85%
# - CPU usage > 80%
```

#### Prometheus Alert Rules
```yaml
# Verify alert rules are loaded
groups:
  - name: repo-scanner-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}%"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s"
```

### Log Aggregation Setup

#### ELK Stack Configuration
```bash
# 1. Verify log ingestion
kubectl logs -n repo-scanner deployment/repo-scanner --tail=50

# 2. Check Elasticsearch indices
curl -X GET "elasticsearch:9200/_cat/indices/repo-scanner-*"

# 3. Verify Kibana dashboards
# Access: https://kibana.yourcompany.com/app/kibana#/dashboard/repo-scanner-logs

# 4. Set up log alerts
# - Error log volume spikes
# - Specific error patterns
# - Performance degradation indicators
```

### Automated Health Checks

#### Scheduled Health Monitoring
```bash
# Create cron job for automated health checks
cat << 'EOF' > /etc/cron.d/repo-scanner-health
# Run health checks every 5 minutes
*/5 * * * * root /usr/local/bin/repo-scanner-health-check.sh
EOF

# Health check script
cat << 'EOF' > /usr/local/bin/repo-scanner-health-check.sh
#!/bin/bash

# Health check logic
HEALTH_URL="https://scanner.yourcompany.com/health"
RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null $HEALTH_URL)

if [ "$RESPONSE" -ne 200 ]; then
    echo "$(date): Health check failed with code $RESPONSE" >> /var/log/repo-scanner-health.log
    # Send alert
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"Health check failed"}' \
        $SLACK_WEBHOOK_URL
fi
EOF
```

## Performance Monitoring

### Key Performance Indicators (KPIs)

#### System Performance Metrics
- **Response Time**: API response time (target: < 2 seconds 95th percentile)
- **Throughput**: Requests per second (target: > 100 RPS)
- **Error Rate**: HTTP error percentage (target: < 1%)
- **Availability**: Uptime percentage (target: > 99.9%)

#### Resource Utilization Metrics
- **CPU Usage**: Container CPU utilization (target: < 70%)
- **Memory Usage**: Container memory utilization (target: < 80%)
- **Disk Usage**: Persistent volume utilization (target: < 85%)
- **Network I/O**: Network throughput and latency

#### Business Metrics
- **Scan Success Rate**: Percentage of successful scans (target: > 95%)
- **Scan Duration**: Average scan completion time (target: < 10 minutes)
- **User Satisfaction**: Based on feedback and usage patterns
- **Data Quality**: Accuracy of scan results

### Performance Trending Analysis

#### Weekly Performance Review
```bash
# 1. Generate performance report
python scripts/performance_analysis.py \
  --start-date $(date -d '7 days ago' +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  --output report.json

# 2. Analyze trends:
# - Performance degradation patterns
# - Resource utilization trends
# - Error rate patterns
# - User behavior changes

# 3. Identify optimization opportunities:
# - Code performance improvements
# - Infrastructure scaling needs
# - Caching strategy adjustments
# - Database query optimizations
```

#### Monthly Performance Assessment
```bash
# 1. Capacity planning analysis
python scripts/capacity_planning.py \
  --historical-data 90d \
  --growth-rate 0.15 \
  --output capacity-plan.json

# 2. Review:
# - Resource utilization forecasts
# - Scaling requirements
# - Cost optimization opportunities
# - Performance bottleneck identification

# 3. Implement improvements:
# - Resource limit adjustments
# - Auto-scaling configuration updates
# - Infrastructure optimizations
```

## Security Monitoring

### Security Event Monitoring
```bash
# 1. Authentication failure monitoring
# Monitor for brute force attempts
kubectl logs -n repo-scanner deployment/repo-scanner | grep "authentication failed"

# 2. Access pattern analysis
# Identify unusual access patterns
kubectl logs -n repo-scanner deployment/repo-scanner | \
  grep "access" | \
  awk '{print $1, $4}' | \
  sort | \
  uniq -c | \
  sort -nr | \
  head -10

# 3. Data exfiltration detection
# Monitor for large data transfers
kubectl logs -n repo-scanner deployment/repo-scanner | \
  grep "data export" | \
  awk '{sum += $NF} END {print "Total exported: " sum " bytes"}'
```

### Compliance Monitoring
```bash
# 1. Audit log verification
# Ensure all actions are logged
kubectl logs -n repo-scanner deployment/repo-scanner | \
  grep "audit" | \
  wc -l

# 2. Data retention compliance
# Verify data cleanup processes
python scripts/data_retention_check.py

# 3. Access control verification
# Regular RBAC and permission audits
kubectl get rolebindings -n repo-scanner
kubectl get clusterrolebindings | grep repo-scanner
```

## Incident Detection and Response

### Automated Alert Response
```bash
# Alert response automation script
cat << 'EOF' > /usr/local/bin/alert-response.sh
#!/bin/bash

ALERT_NAME=$1
SEVERITY=$2

case $ALERT_NAME in
    "HighErrorRate")
        # Auto-scale application
        kubectl scale deployment/repo-scanner --replicas=5 -n repo-scanner
        # Send notification
        ;;
    "PodCrash")
        # Restart deployment
        kubectl rollout restart deployment/repo-scanner -n repo-scanner
        # Investigate logs
        ;;
    "HighMemoryUsage")
        # Check memory usage
        kubectl top pods -n repo-scanner
        # Scale if needed
        ;;
esac
EOF
```

### Incident Response Validation
```bash
# Post-incident validation checklist
VALIDATION_CHECKS=(
    "System health restored"
    "All services accessible"
    "Data integrity verified"
    "Monitoring alerts cleared"
    "Performance within normal ranges"
    "Security controls intact"
    "Documentation updated"
    "Stakeholders notified"
)

for check in "${VALIDATION_CHECKS[@]}"; do
    echo -n "✓ $check: "
    read -p "Confirm (y/n): " response
    if [ "$response" != "y" ]; then
        echo "❌ Validation failed for: $check"
        exit 1
    fi
done

echo "✅ All post-incident validations passed"
```

## Validation Checklists

### Daily Validation Checklist
- [ ] System health endpoints responding
- [ ] All pods in running state
- [ ] Resource usage within limits
- [ ] No critical alerts active
- [ ] Backup jobs completed successfully
- [ ] Log ingestion working
- [ ] Security scans passed

### Weekly Validation Checklist
- [ ] Performance metrics within targets
- [ ] Error rates below thresholds
- [ ] Capacity planning updated
- [ ] Security patches applied
- [ ] Documentation reviewed and updated
- [ ] Team knowledge sharing completed

### Monthly Validation Checklist
- [ ] Compliance audit completed
- [ ] Disaster recovery tested
- [ ] Performance optimization implemented
- [ ] Cost optimization reviewed
- [ ] Stakeholder reports delivered
- [ ] System architecture review completed

## Reporting and Communication

### Daily Status Report
```bash
# Generate daily status report
python scripts/generate_daily_report.py \
  --date $(date +%Y-%m-%d) \
  --output /reports/daily-status-$(date +%Y%m%d).html

# Report contents:
# - System availability
# - Performance metrics
# - Incident summary
# - Upcoming maintenance
# - Key achievements
```

### Weekly Operations Review
```bash
# Generate weekly operations report
python scripts/generate_weekly_report.py \
  --week $(date +%V) \
  --output /reports/weekly-ops-$(date +%Y%V).pdf

# Report contents:
# - Performance trends
# - Incident analysis
# - Capacity utilization
# - Security events
# - Improvement recommendations
```

### Monthly Executive Summary
```bash
# Generate monthly executive summary
python scripts/generate_monthly_summary.py \
  --month $(date +%Y-%m) \
  --output /reports/monthly-summary-$(date +%Y%m).pdf

# Report contents:
# - SLA/SLO compliance
# - Cost analysis
# - Risk assessment
- Business value metrics
- Strategic recommendations
```

## Continuous Improvement

### Feedback Collection
```bash
# User feedback collection
# - In-app feedback forms
# - Support ticket analysis
# - User interview sessions
# - Performance feedback surveys

# Process feedback:
# 1. Categorize feedback types
# 2. Prioritize improvement opportunities
# 3. Plan implementation roadmap
# 4. Track progress and outcomes
```

### System Optimization
```bash
# Continuous optimization process:
# 1. Monitor performance metrics
# 2. Identify bottlenecks and inefficiencies
# 3. Implement optimizations
# 4. Measure improvement impact
# 5. Document lessons learned

# Optimization areas:
# - Application code improvements
# - Database query optimization
# - Infrastructure scaling
# - Caching strategy enhancements
# - Network optimization
```

---

**Document Version**: 1.0
**Last Updated**: 23 December 2025
**Review Date**: 23 January 2026
**Approved By**: Operations Team Lead
**Training Required**: All operations and development personnel