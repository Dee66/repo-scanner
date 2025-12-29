# Production Monitoring and Alerting Setup

## Overview
This document defines the production monitoring and alerting configuration for the Repository Intelligence Scanner to maintain 99.999% uptime and reliability.

## Monitoring Architecture

### Components
1. **Application Metrics** - Service health, performance, and business metrics
2. **Infrastructure Metrics** - System resources, network, and container health
3. **External Dependencies** - Database, APIs, and third-party services
4. **Business Metrics** - Scan success rates, processing times, and user satisfaction

### Monitoring Stack
- **Metrics Collection**: Prometheus with custom exporters
- **Visualization**: Grafana dashboards
- **Alerting**: AlertManager with PagerDuty integration
- **Logging**: ELK stack (Elasticsearch, Logstash, Kibana)
- **Tracing**: Jaeger for distributed tracing

## Key Metrics to Monitor

### Service Health Metrics
```yaml
# Application availability
- metric: service_uptime
  type: gauge
  description: Service availability percentage
  threshold: > 99.999

# Request success rate
- metric: request_success_rate
  type: histogram
  description: Percentage of successful requests
  buckets: [0.5, 0.9, 0.95, 0.99, 0.999]
  threshold: > 99.9

# Response time
- metric: request_duration_seconds
  type: histogram
  description: Request processing time
  buckets: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
  threshold_p95: < 2.0 seconds
```

### Business Metrics
```yaml
# Scan completion rate
- metric: scan_completion_rate
  type: gauge
  description: Percentage of scans completed successfully
  threshold: > 99.5

# Repository processing time
- metric: repository_scan_duration
  type: histogram
  description: Time to scan a repository
  threshold_p95: < 300 seconds

# Queue depth
- metric: analysis_queue_depth
  type: gauge
  description: Number of pending analysis requests
  threshold: < 100
```

### Infrastructure Metrics
```yaml
# CPU usage
- metric: cpu_usage_percent
  type: gauge
  description: CPU utilization percentage
  threshold: < 80

# Memory usage
- metric: memory_usage_percent
  type: gauge
  description: Memory utilization percentage
  threshold: < 85

# Disk usage
- metric: disk_usage_percent
  type: gauge
  description: Disk utilization percentage
  threshold: < 90

# Network I/O
- metric: network_bytes_per_second
  type: counter
  description: Network traffic rate
  threshold: Based on baseline
```

## Alerting Rules

### Critical Alerts (Page immediately)
```yaml
# Service down
alert: ServiceDown
expr: up{job="repo-scanner"} == 0
for: 1m
labels:
  severity: critical
annotations:
  summary: "Repository Scanner service is down"
  description: "Service {{ $labels.instance }} has been down for 1 minute"

# High error rate
alert: HighErrorRate
expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
for: 2m
labels:
  severity: critical
annotations:
  summary: "High error rate detected"
  description: "Error rate is {{ $value | printf "%.2f" }}%"

# SLA breach
alert: SLABreach
expr: service_uptime < 0.99999
for: 5m
labels:
  severity: critical
annotations:
  summary: "99.999% SLA breach detected"
  description: "Service uptime dropped below 99.999% ({{ $value | printf "%.5f" }})"
```

### Warning Alerts (Page during business hours)
```yaml
# Performance degradation
alert: PerformanceDegradation
expr: histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m])) > 5.0
for: 5m
labels:
  severity: warning
annotations:
  summary: "Response time degradation"
  description: "95th percentile response time is {{ $value | printf "%.2f" }}s"

# Queue backup
alert: QueueBackup
expr: analysis_queue_depth > 50
for: 3m
labels:
  severity: warning
annotations:
  summary: "Analysis queue backing up"
  description: "Queue depth is {{ $value }}"

# Resource usage warning
alert: HighResourceUsage
expr: cpu_usage_percent > 70 OR memory_usage_percent > 75
for: 5m
labels:
  severity: warning
annotations:
  summary: "High resource usage"
  description: "CPU: {{ $labels.cpu_usage_percent }}%, Memory: {{ $labels.memory_usage_percent }}%"
```

### Info Alerts (Log only)
```yaml
# Feature flag usage
alert: FeatureFlagUsage
expr: feature_flag_enabled_total > 0
for: 0m
labels:
  severity: info
annotations:
  summary: "Feature flag activated"
  description: "Feature {{ $labels.flag }} is now {{ $labels.state }}"

# Deployment completed
alert: DeploymentCompleted
expr: deployment_status == 1
for: 0m
labels:
  severity: info
annotations:
  summary: "Deployment completed"
  description: "Version {{ $labels.version }} deployed to {{ $labels.environment }}"
```

## Dashboard Configuration

### Main Service Dashboard
```
Panels:
1. Service Uptime (99.999% target line)
2. Request Rate and Success Rate
3. Response Time Percentiles (p50, p95, p99)
4. Error Rate by Endpoint
5. Queue Depth and Processing Rate
6. Resource Usage (CPU, Memory, Disk)
7. Business Metrics (Scan Success, Processing Time)
```

### Incident Response Dashboard
```
Panels:
1. Current Alerts (Active and Recent)
2. Service Dependencies Status
3. Recent Error Logs
4. Performance During Incident
5. User Impact Assessment
6. Recovery Timeline
```

## Alert Response Procedures

### Critical Alert Response (P1)
1. **Acknowledge within 5 minutes**
2. **Assess impact and notify stakeholders**
3. **Begin investigation using runbook**
4. **Implement temporary mitigation if needed**
5. **Escalate to on-call engineer if unresolved in 15 minutes**
6. **Provide hourly updates until resolved**

### Warning Alert Response (P2)
1. **Acknowledge within 30 minutes during business hours**
2. **Assess if immediate action required**
3. **Schedule investigation for next business day if non-critical**
4. **Document findings and remediation plan**

### Info Alert Response (P3)
1. **Log for awareness**
2. **No immediate action required**
3. **Review during regular maintenance windows**

## Runbook Procedures

### Service Restart Procedure
```
1. Check current status and error logs
2. Verify dependencies are healthy
3. Attempt graceful restart
4. Monitor startup logs
5. Validate service health checks
6. Notify stakeholders of completion
```

### Database Connection Issues
```
1. Check database connectivity
2. Verify connection pool settings
3. Review recent schema changes
4. Check for connection leaks
5. Implement connection pool reset if needed
6. Monitor for recurrence
```

### High Memory Usage
```
1. Check memory usage trends
2. Analyze heap dumps if available
3. Identify memory leaks
4. Implement garbage collection tuning
5. Consider horizontal scaling
6. Monitor after changes
```

## SLA Monitoring

### Uptime Calculation
```python
def calculate_uptime(monitoring_window_days=30):
    """
    Calculate service uptime over the monitoring window.
    Target: 99.999% (5.256 minutes downtime per month)
    """
    total_seconds = monitoring_window_days * 24 * 60 * 60
    downtime_seconds = get_total_downtime_seconds(monitoring_window_days)
    uptime_percentage = ((total_seconds - downtime_seconds) / total_seconds) * 100

    return {
        'uptime_percentage': uptime_percentage,
        'downtime_minutes': downtime_seconds / 60,
        'sla_met': uptime_percentage >= 99.999
    }
```

### SLA Dashboard
```
Monthly Uptime: XX.XXXX%
Target: 99.999%
Remaining Downtime Budget: X.XX minutes
Incident Count: X (Target: 0)
MTTR: XX minutes (Target: < 15 min)
```

## Integration Points

### CI/CD Pipeline Integration
- Automated deployment validation
- Pre-deployment smoke tests
- Post-deployment health checks
- Rollback automation triggers

### Incident Management Integration
- Automatic ticket creation
- Stakeholder notification
- Post-mortem template population
- Knowledge base updates

### Communication Integration
- Slack alerts for warnings
- Email notifications for critical alerts
- Status page updates
- Executive summary reports

## Testing and Validation

### Alert Testing
```bash
# Test critical alert
curl -X POST http://alertmanager:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{"labels":{"alertname":"TestCritical","severity":"critical"},"annotations":{"summary":"Test alert"}}]'

# Test monitoring endpoint
curl http://prometheus:9090/api/v1/query?query=up
```

### Dashboard Validation
- Verify all panels load correctly
- Test alert thresholds with synthetic data
- Validate time range selections
- Check mobile responsiveness

## Maintenance Procedures

### Weekly Tasks
- Review alert history and false positives
- Update dashboard thresholds based on trends
- Archive old logs and metrics
- Test backup monitoring systems

### Monthly Tasks
- SLA compliance review
- Alert rule optimization
- Dashboard cleanup and reorganization
- Team training refresh

### Quarterly Tasks
- Monitoring stack upgrades
- Security assessment of monitoring infrastructure
- Cost optimization review
- Disaster recovery testing

## Contact Information

**Monitoring Owner:** [Name]
**Alert Manager:** [Name]
**SRE Lead:** [Name]
**DevOps Lead:** [Name]

**Escalation Path:**
1. On-call Engineer
2. SRE Lead
3. DevOps Lead
4. Engineering Director
5. CTO