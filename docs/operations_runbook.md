# Repository Intelligence Scanner - Production Operations Runbook

## Overview

This operations runbook provides comprehensive procedures for operating and maintaining the Repository Intelligence Scanner in production environments. It covers all aspects of system management, monitoring, troubleshooting, and maintenance.

**Version:** 1.0.0
**Last Updated:** 2025-12-29
**Applies To:** Production deployments
**Contact:** Operations Team

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Startup and Shutdown Procedures](#startup-and-shutdown-procedures)
3. [Monitoring and Alerting](#monitoring-and-alerting)
4. [Configuration Management](#configuration-management)
5. [Backup and Recovery](#backup-and-recovery)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Maintenance Procedures](#maintenance-procedures)
8. [Emergency Response](#emergency-response)
9. [Performance Optimization](#performance-optimization)
10. [Security Operations](#security-operations)

## System Architecture

### High-Level Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   API Server    │    │   Monitoring    │
│   (Ingress)     │◄──►│   (FastAPI)     │◄──►│   Stack         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Worker Pods   │    │   Database      │    │   Alerting      │
│   (Analysis)    │    │   (PostgreSQL)  │    │   & Dashboards  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cache/Redis   │    │   Storage       │    │   Logging       │
│   (Sessions)    │    │   (PVC)         │    │   Aggregation   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Services

- **API Server**: FastAPI-based REST API for repository scanning and configuration management
- **Worker Processes**: Asynchronous analysis tasks with circuit breaker protection
- **Database**: PostgreSQL for metadata, results, and audit logs
- **Cache**: Redis for session management and temporary data
- **Monitoring**: Prometheus metrics collection and Grafana dashboards
- **Security**: Secure configuration management with encryption and audit trails

## Startup and Shutdown Procedures

### Normal Startup Sequence

#### 1. Infrastructure Startup
```bash
# Verify Kubernetes cluster health
kubectl get nodes
kubectl get pods -A

# Start supporting services first
kubectl apply -f k8s/postgresql/
kubectl apply -f k8s/redis/

# Wait for services to be ready
kubectl wait --for=condition=ready pod -l app=postgresql --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis --timeout=300s
```

#### 2. Application Startup
```bash
# Deploy the application
helm upgrade --install repo-scanner ./helm/repo-scanner \
  --namespace repo-scanner \
  --create-namespace \
  --wait

# Verify deployment
kubectl get pods -n repo-scanner
kubectl get services -n repo-scanner
kubectl get ingress -n repo-scanner
```

#### 3. Service Validation
```bash
# Test API endpoints
curl -f https://scanner.company.com/health
curl -f https://scanner.company.com/api/config/list

# Verify monitoring
curl -f http://prometheus.repo-scanner.svc.cluster.local:9090/-/healthy
curl -f http://grafana.repo-scanner.svc.cluster.local:3000/api/health
```

### Graceful Shutdown Sequence

#### 1. Stop Accepting New Requests
```bash
# Set maintenance mode
kubectl set env deployment/repo-scanner MAINTENANCE_MODE=true -n repo-scanner

# Wait for active requests to complete (check metrics)
kubectl logs -f deployment/repo-scanner -n repo-scanner | grep "active_requests"
```

#### 2. Shutdown Application
```bash
# Scale down to zero
kubectl scale deployment repo-scanner --replicas=0 -n repo-scanner

# Wait for pods to terminate gracefully
kubectl wait --for=delete pod -l app=repo-scanner --timeout=300s -n repo-scanner
```

#### 3. Shutdown Supporting Services
```bash
# Stop monitoring (optional, for maintenance)
kubectl scale deployment prometheus --replicas=0 -n monitoring
kubectl scale deployment grafana --replicas=0 -n monitoring

# Database and cache can remain running for other services
```

### Emergency Shutdown
```bash
# Immediate shutdown (use only in emergencies)
kubectl delete namespace repo-scanner --ignore-not-found=true --timeout=60s

# Force delete stuck resources
kubectl delete pod --force --grace-period=0 -l app=repo-scanner -n repo-scanner
```

## Monitoring and Alerting

### Key Metrics to Monitor

#### Application Metrics
- **Request Rate**: API requests per second
- **Response Time**: P95 response time < 5 seconds
- **Error Rate**: < 1% of total requests
- **Active Connections**: Current concurrent connections

#### System Metrics
- **CPU Usage**: < 70% sustained
- **Memory Usage**: < 80% of allocated
- **Disk Usage**: < 85% of available
- **Network I/O**: Monitor for bottlenecks

#### Business Metrics
- **Scan Success Rate**: > 95% successful scans
- **Analysis Time**: < 30 seconds average
- **Queue Depth**: < 100 pending scans

### Alert Definitions

#### Critical Alerts (Immediate Response < 5 minutes)
- **Service Down**: API server unavailable
- **Database Connection Lost**: Cannot connect to PostgreSQL
- **High Error Rate**: > 10% error rate for 5 minutes
- **Security Breach**: Unauthorized access detected

#### Warning Alerts (Response < 15 minutes)
- **High CPU/Memory**: Resource usage > 80%
- **Slow Response Time**: P95 > 10 seconds
- **Queue Backlog**: > 500 pending scans
- **Disk Space Low**: < 10% free space

#### Info Alerts (Response < 1 hour)
- **Configuration Change**: Audit log entries
- **Version Mismatch**: Component version drift
- **Deprecation Warnings**: Outdated configurations

### Alert Response Procedures

#### Service Down Alert
```bash
# 1. Check pod status
kubectl get pods -n repo-scanner

# 2. Check pod logs
kubectl logs deployment/repo-scanner -n repo-scanner --previous

# 3. Check events
kubectl get events -n repo-scanner --sort-by=.metadata.creationTimestamp | tail -20

# 4. Restart deployment
kubectl rollout restart deployment/repo-scanner -n repo-scanner

# 5. If restart fails, check resource constraints
kubectl describe pod <pod-name> -n repo-scanner
```

#### High Error Rate Alert
```bash
# 1. Check application logs for error patterns
kubectl logs deployment/repo-scanner -n repo-scanner --since=10m | grep ERROR

# 2. Check metrics for error breakdown
curl http://prometheus:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[5m])

# 3. Check external dependencies
kubectl exec -it deployment/postgresql -- pg_isready
kubectl exec -it deployment/redis -- redis-cli ping

# 4. Check configuration validity
curl https://scanner.company.com/api/config/validate
```

## Configuration Management

### Secure Configuration System

The system uses enterprise-grade secure configuration management with:
- Encrypted storage for sensitive data
- Schema validation for all settings
- Audit trails for all changes
- API-based configuration management

### Configuration Categories

#### Core Application Settings
```yaml
api_server:
  enabled: true
  host: "0.0.0.0"
  port: 8080
  workers: 4

logging:
  level: "INFO"
  max_file_size: 10485760  # 10MB
```

#### Security Settings
```yaml
security:
  rate_limit_per_minute: 100
  max_file_size_mb: 100
  session_timeout: 3600

circuit_breaker:
  enabled: true
  failure_threshold: 5
  recovery_timeout: 60
```

#### Monitoring Settings
```yaml
health_monitoring:
  enabled: true
  uptime_sla_target: 99.999
  health_check_interval: 30

metrics:
  enabled: true
  collection_interval: 15
  retention_period: 30
```

### Configuration Management Procedures

#### Viewing Current Configuration
```bash
# List all configuration keys
curl -H "Authorization: Bearer <token>" \
  https://scanner.company.com/api/config/list

# Get specific configuration value
curl -H "Authorization: Bearer <token>" \
  https://scanner.company.com/api/config/get/api_server.port
```

#### Updating Configuration
```bash
# Set configuration value
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"key": "security.rate_limit_per_minute", "value": 200}' \
  https://scanner.company.com/api/config/set
```

#### Configuration Validation
```bash
# Validate configuration changes before applying
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"key": "api_server.port", "value": 9090}' \
  https://scanner.company.com/api/config/validate
```

#### Audit Trail Review
```bash
# View recent configuration changes
curl -H "Authorization: Bearer <token>" \
  https://scanner.company.com/api/config/audit

# Filter by time range
curl -H "Authorization: Bearer <token>" \
  "https://scanner.company.com/api/config/audit?since=2025-12-01"
```

### Configuration Backup and Recovery

#### Backup Configuration
```bash
# Export all configuration
curl -H "Authorization: Bearer <token>" \
  https://scanner.company.com/api/config/export > config_backup_$(date +%Y%m%d).json

# Backup encrypted configuration files
kubectl cp repo-scanner-pod:/app/config/secure_config.enc ./backups/ -n repo-scanner
```

#### Restore Configuration
```bash
# Import configuration from backup
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d @config_backup_20251229.json \
  https://scanner.company.com/api/config/import
```

## Backup and Recovery

### Backup Strategy

#### Daily Backups
- **Application Data**: Database dumps every 6 hours
- **Configuration**: Encrypted configuration files daily
- **Logs**: Compressed log archives weekly
- **Metrics**: Prometheus data retention 30 days

#### Weekly Backups
- **Full System Backup**: Complete application state
- **Code Repository**: Tagged releases and configurations
- **Documentation**: Updated runbooks and procedures

### Backup Procedures

#### Database Backup
```bash
# Create database backup
kubectl exec -it deployment/postgresql -n repo-scanner -- pg_dump -U repo_user repo_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Compress backup
gzip backup_$(date +%Y%m%d_%H%M%S).sql

# Upload to secure storage
aws s3 cp backup_$(date +%Y%m%d_%H%M%S).sql.gz s3://repo-scanner-backups/database/
```

#### Configuration Backup
```bash
# Export configuration via API
curl -H "Authorization: Bearer <token>" \
  https://scanner.company.com/api/config/export > config_backup_$(date +%Y%m%d).json

# Backup configuration files
kubectl cp repo-scanner-pod:/app/config/ ./backups/config_$(date +%Y%m%d)/ -n repo-scanner
```

#### Log Backup
```bash
# Compress current logs
kubectl exec deployment/repo-scanner -n repo-scanner -- tar czf /tmp/logs_$(date +%Y%m%d).tar.gz /app/logs/

# Copy compressed logs
kubectl cp repo-scanner-pod:/tmp/logs_$(date +%Y%m%d).tar.gz ./backups/ -n repo-scanner
```

### Recovery Procedures

#### Database Recovery
```bash
# Stop application to prevent data corruption
kubectl scale deployment repo-scanner --replicas=0 -n repo-scanner

# Restore database from backup
kubectl exec -it deployment/postgresql -n repo-scanner -- psql -U repo_user -d repo_db < backup_20251229.sql

# Restart application
kubectl scale deployment repo-scanner --replicas=3 -n repo-scanner
```

#### Configuration Recovery
```bash
# Import configuration from backup
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d @config_backup_20251229.json \
  https://scanner.company.com/api/config/import
```

#### Full System Recovery
```bash
# 1. Restore from latest backup
# 2. Verify data integrity
# 3. Test application functionality
# 4. Update monitoring and alerting
# 5. Notify stakeholders of recovery completion
```

### Recovery Time Objectives (RTO)
- **Critical Services**: < 1 hour
- **Application Services**: < 4 hours
- **Full System**: < 24 hours

### Recovery Point Objectives (RPO)
- **Critical Data**: < 1 hour data loss
- **Application Data**: < 6 hours data loss
- **Logs and Metrics**: < 24 hours data loss

## Troubleshooting Guide

### Common Issues and Solutions

#### High Memory Usage
**Symptoms**: Pod restarts, OOM kills, slow response times

**Diagnosis**:
```bash
# Check memory usage
kubectl top pods -n repo-scanner

# Check memory limits
kubectl describe pod <pod-name> -n repo-scanner

# Check application memory metrics
curl http://prometheus:9090/api/v1/query?query=container_memory_usage_bytes{pod=~".*repo-scanner.*"}
```

**Solutions**:
1. Increase memory limits in deployment
2. Optimize application memory usage
3. Scale horizontally to distribute load
4. Check for memory leaks in application code

#### Slow API Response Times
**Symptoms**: P95 response time > 5 seconds, user complaints

**Diagnosis**:
```bash
# Check response time metrics
curl http://prometheus:9090/api/v1/query?query=http_request_duration_seconds{quantile="0.95"}

# Check database query performance
kubectl exec -it deployment/postgresql -- psql -U repo_user -d repo_db -c "SELECT * FROM pg_stat_activity;"

# Check cache hit rates
kubectl exec -it deployment/redis -- redis-cli info stats
```

**Solutions**:
1. Optimize database queries and add indexes
2. Increase cache size and TTL
3. Scale application pods
4. Check network latency to external services

#### Database Connection Issues
**Symptoms**: Error rate spikes, "connection refused" errors

**Diagnosis**:
```bash
# Check database pod status
kubectl get pods -l app=postgresql -n repo-scanner

# Check database logs
kubectl logs deployment/postgresql -n repo-scanner

# Test database connectivity
kubectl exec -it deployment/repo-scanner -- nc -zv postgresql 5432
```

**Solutions**:
1. Restart database pods
2. Check connection pool settings
3. Verify database credentials
4. Check network policies and security groups

#### Configuration Validation Errors
**Symptoms**: Application fails to start, configuration-related errors

**Diagnosis**:
```bash
# Check configuration validation
curl https://scanner.company.com/api/config/validate

# Check configuration audit trail
curl -H "Authorization: Bearer <token>" https://scanner.company.com/api/config/audit | tail -10

# Check application logs for configuration errors
kubectl logs deployment/repo-scanner -n repo-scanner | grep -i config
```

**Solutions**:
1. Review recent configuration changes
2. Validate configuration against schema
3. Roll back to previous working configuration
4. Check environment variable overrides

### Debug Commands Reference

#### Application Debugging
```bash
# Get detailed pod information
kubectl describe pod <pod-name> -n repo-scanner

# Check application logs with timestamps
kubectl logs deployment/repo-scanner -n repo-scanner --timestamps

# Execute commands in running container
kubectl exec -it deployment/repo-scanner -n repo-scanner -- /bin/bash

# Check application health endpoints
curl https://scanner.company.com/health
curl https://scanner.company.com/metrics
```

#### Database Debugging
```bash
# Check database connections
kubectl exec -it deployment/postgresql -- psql -U repo_user -d repo_db -c "SELECT count(*) FROM pg_stat_activity;"

# Check database size and growth
kubectl exec -it deployment/postgresql -- psql -U repo_user -d repo_db -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;"

# Check slow queries
kubectl exec -it deployment/postgresql -- psql -U repo_user -d repo_db -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

#### Network Debugging
```bash
# Check service endpoints
kubectl get endpoints -n repo-scanner

# Test service connectivity
kubectl run test-pod --image=busybox --rm -it --restart=Never -- nslookup repo-scanner.repo-scanner.svc.cluster.local

# Check network policies
kubectl get networkpolicies -n repo-scanner

# Test external connectivity
kubectl exec -it deployment/repo-scanner -- curl -I https://api.github.com
```

## Maintenance Procedures

### Daily Maintenance

#### Morning System Check (9:00 AM)
```bash
# 1. Check system status
kubectl get nodes
kubectl get pods -A | grep -v Running

# 2. Review overnight alerts
# Check AlertManager and Grafana dashboards

# 3. Verify backup completion
# Check backup logs and success notifications

# 4. Check resource utilization
kubectl top nodes
kubectl top pods -A
```

#### Evening Log Rotation (6:00 PM)
```bash
# 1. Rotate application logs
kubectl exec deployment/repo-scanner -- logrotate /etc/logrotate.d/repo-scanner

# 2. Archive old logs
kubectl exec deployment/repo-scanner -- find /app/logs -name "*.log.1" -exec gzip {} \;

# 3. Clean up old log archives (keep 30 days)
kubectl exec deployment/repo-scanner -- find /app/logs -name "*.gz" -mtime +30 -delete
```

### Weekly Maintenance

#### Monday Morning (9:00 AM)
```bash
# 1. Security review
# - Review failed authentication attempts
# - Check for unusual access patterns
# - Review configuration audit trail

# 2. Performance analysis
# - Analyze weekly performance metrics
# - Review error rates and patterns
# - Check resource utilization trends

# 3. Capacity planning
# - Project resource needs for next month
# - Review auto-scaling effectiveness
# - Plan infrastructure upgrades if needed
```

#### Friday Afternoon (4:00 PM)
```bash
# 1. Backup verification
# - Test backup restoration in staging
# - Verify backup integrity
# - Update backup retention policies

# 2. Certificate renewal check
# - Check SSL certificate expiration
# - Renew certificates if needed
# - Update certificate stores
```

### Monthly Maintenance

#### First Monday (9:00 AM)
```bash
# 1. System optimization
# - Database maintenance (VACUUM, REINDEX)
# - Application performance tuning
# - Cache optimization

# 2. Security updates
# - Apply security patches
# - Update dependencies
# - Review security configurations

# 3. Compliance review
# - Audit log review
# - Access control verification
# - Data retention compliance
```

#### Third Monday (9:00 AM)
```bash
# 1. Capacity planning review
# - Analyze usage trends
# - Review scaling policies
# - Plan infrastructure changes

# 2. Disaster recovery testing
# - Test backup restoration procedures
# - Validate failover scenarios
# - Update recovery runbooks
```

### Quarterly Maintenance

#### End of Quarter
```bash
# 1. Major version updates
# - Plan application upgrades
# - Test compatibility with new versions
# - Schedule maintenance windows

# 2. Infrastructure review
# - Review cloud resource utilization
# - Optimize costs
# - Plan infrastructure modernization

# 3. Process improvements
# - Review incident response effectiveness
# - Update runbooks and procedures
# - Conduct lessons learned sessions
```

## Emergency Response

### Incident Response Process

#### Phase 1: Detection (0-5 minutes)
1. **Alert Triggered**: Monitoring system detects anomaly
2. **Initial Assessment**: On-call engineer evaluates severity
3. **Notification**: Alert team members and stakeholders
4. **Documentation**: Create incident ticket and start timeline

#### Phase 2: Assessment (5-30 minutes)
1. **Impact Analysis**: Determine affected systems and users
2. **Root Cause Investigation**: Gather logs and metrics
3. **Containment Planning**: Develop immediate mitigation steps
4. **Communication**: Update stakeholders on status

#### Phase 3: Resolution (30 minutes - 4 hours)
1. **Implement Fix**: Apply temporary or permanent solution
2. **Test Solution**: Verify fix resolves the issue
3. **Monitor Recovery**: Ensure system stability
4. **Document Changes**: Record all changes made

#### Phase 4: Post-Incident (4-24 hours)
1. **Detailed Analysis**: Complete root cause analysis
2. **Process Improvements**: Identify and implement fixes
3. **Documentation Updates**: Update runbooks and procedures
4. **Lessons Learned**: Conduct post-mortem meeting

### Critical Incident Playbooks

#### Complete Service Outage
**Trigger**: API server unavailable, no response on health endpoint

**Immediate Actions**:
```bash
# 1. Check cluster status
kubectl get nodes
kubectl get pods -A

# 2. Attempt quick restart
kubectl rollout restart deployment/repo-scanner -n repo-scanner

# 3. Check logs for errors
kubectl logs deployment/repo-scanner -n repo-scanner --previous

# 4. If restart fails, scale up resources
kubectl scale deployment/repo-scanner --replicas=5 -n repo-scanner
```

**Escalation Path**:
- 5 minutes: Engineering lead
- 15 minutes: Engineering manager
- 30 minutes: CTO and customer success

#### Data Loss Incident
**Trigger**: Database corruption or accidental deletion detected

**Immediate Actions**:
```bash
# 1. Stop all write operations
kubectl scale deployment/repo-scanner --replicas=0 -n repo-scanner

# 2. Assess data loss extent
kubectl exec -it deployment/postgresql -- pg_dump -U repo_user repo_db | wc -l

# 3. Restore from backup
kubectl exec -it deployment/postgresql -- psql -U repo_user -d repo_db < latest_backup.sql

# 4. Verify data integrity
kubectl exec -it deployment/postgresql -- psql -U repo_user -d repo_db -c "SELECT count(*) FROM scan_results;"
```

#### Security Breach Response
**Trigger**: Unauthorized access or suspicious activity detected

**Immediate Actions**:
```bash
# 1. Isolate affected systems
kubectl cordon <affected-node>

# 2. Revoke compromised credentials
# Rotate API keys, database passwords, service accounts

# 3. Enable enhanced logging
kubectl set env deployment/repo-scanner LOG_LEVEL=DEBUG -n repo-scanner

# 4. Preserve evidence
# Take forensic snapshots before making changes
```

### Communication Templates

#### Initial Customer Notification
```
Subject: Repository Scanner Service Incident - Update

Dear Customer,

We have detected an incident affecting the Repository Intelligence Scanner service. Our team is actively investigating and working to resolve the issue.

Current Status: Investigating
Impact: [Brief description of impact]
Estimated Resolution: [Time estimate]

We will provide updates every 30 minutes. For urgent issues, contact our support team at [contact info].

Best regards,
Operations Team
```

#### Internal Status Update
```
INCIDENT UPDATE - [Incident ID]

Status: [Investigating/Resolving/Resolved]
Timeline:
- [Time] Incident detected
- [Time] Initial assessment complete
- [Time] Root cause identified
- [Time] Fix implemented

Current Actions:
- [Action 1]
- [Action 2]

Next Steps:
- [Step 1]
- [Step 2]

On-call: [Engineer Name]
Escalation: [Manager Name]
```

## Performance Optimization

### Performance Monitoring

#### Key Performance Indicators
- **Response Time**: P95 < 5 seconds, P99 < 10 seconds
- **Throughput**: 100 requests/second sustained
- **Error Rate**: < 1% of total requests
- **Resource Utilization**: CPU < 70%, Memory < 80%

#### Performance Baselines
- **Small Repository (< 1MB)**: < 5 seconds analysis time
- **Medium Repository (1-10MB)**: < 15 seconds analysis time
- **Large Repository (10-100MB)**: < 30 seconds analysis time
- **API Response Time**: < 500ms for simple requests

### Optimization Procedures

#### Database Optimization
```bash
# Analyze query performance
kubectl exec -it deployment/postgresql -- psql -U repo_user -d repo_db -c "EXPLAIN ANALYZE SELECT * FROM scan_results WHERE created_at > now() - interval '1 day';"

# Add performance indexes
kubectl exec -it deployment/postgresql -- psql -U repo_user -d repo_db -c "CREATE INDEX CONCURRENTLY idx_scan_results_created_at ON scan_results(created_at);"

# Vacuum and analyze tables
kubectl exec -it deployment/postgresql -- psql -U repo_user -d repo_db -c "VACUUM ANALYZE;"
```

#### Application Optimization
```bash
# Profile application performance
kubectl exec deployment/repo-scanner -- python -m cProfile -s time /app/src/cli.py scan /tmp/test-repo > profile.txt

# Check memory usage patterns
kubectl exec deployment/repo-scanner -- python -c "import psutil; print(psutil.virtual_memory())"

# Optimize cache settings
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"key": "cache.ttl", "value": 3600}' https://scanner.company.com/api/config/set
```

#### Infrastructure Optimization
```bash
# Adjust resource limits based on usage
kubectl patch deployment repo-scanner -n repo-scanner --type='json' -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "2Gi"}]'

# Configure horizontal pod autoscaling
kubectl autoscale deployment repo-scanner --cpu-percent=70 --min=3 --max=10 -n repo-scanner

# Optimize network policies
kubectl apply -f k8s/network-optimized-policy.yaml
```

### Capacity Planning

#### Resource Forecasting
```bash
# Analyze usage trends
kubectl logs deployment/prometheus --since=30d | grep "repo_scanner_requests_total" | awk '{print $1}' | sort | uniq -c

# Project future needs
# - Current peak load: X requests/second
# - Growth rate: Y% per month
# - Projected peak: Z requests/second in 6 months

# Plan infrastructure upgrades
# - Additional nodes for horizontal scaling
# - Database read replicas for read-heavy workloads
# - CDN integration for static assets
```

## Security Operations

### Security Monitoring

#### Continuous Monitoring
- **Log Analysis**: Automated detection of security events
- **Network Traffic**: Monitoring for unusual patterns
- **Access Patterns**: Detection of anomalous authentication
- **Configuration Changes**: Audit trail monitoring

#### Security Alerts
- **Failed Authentication**: > 5 failures per minute
- **Privilege Escalation**: Unauthorized access attempts
- **Data Exfiltration**: Unusual data transfer patterns
- **Configuration Tampering**: Unauthorized configuration changes

### Security Procedures

#### Access Control Review
```bash
# Review RBAC permissions
kubectl get clusterrolebindings,rolebindings -n repo-scanner

# Audit service account permissions
kubectl get serviceaccounts -n repo-scanner -o yaml

# Check pod security contexts
kubectl get pods -n repo-scanner -o jsonpath='{.items[*].spec.containers[*].securityContext}'
```

#### Vulnerability Management
```bash
# Scan container images
trivy image repo-scanner:latest --format json > vulnerability_report.json

# Check dependencies
safety check --json > dependency_vulnerabilities.json

# Update base images
docker build --no-cache -t repo-scanner:latest .
```

#### Incident Response
```bash
# Isolate compromised resources
kubectl cordon <node-name>

# Rotate credentials
kubectl create secret generic new-db-secret --from-literal=password=$(openssl rand -base64 32) -n repo-scanner
kubectl rollout restart deployment/postgresql -n repo-scanner

# Enable enhanced monitoring
kubectl set env deployment/repo-scanner SECURITY_AUDIT=true -n repo-scanner
```

### Compliance Procedures

#### Audit Preparation
```bash
# Generate audit logs
kubectl logs deployment/repo-scanner -n repo-scanner --since=90d > audit_logs.txt

# Export configuration audit trail
curl -H "Authorization: Bearer <token>" https://scanner.company.com/api/config/audit > config_audit.json

# Collect access logs
kubectl exec deployment/repo-scanner -- cat /app/logs/access.log > access_audit.log
```

#### Data Protection
```bash
# Verify encryption at rest
kubectl exec deployment/postgresql -- psql -U repo_user -d repo_db -c "SELECT * FROM pg_stat_ssl;"

# Check data masking
curl https://scanner.company.com/api/config/list | jq '.[] | select(.sensitive == true)'

# Validate backup encryption
openssl enc -d -aes-256-cbc -in encrypted_backup.enc -out decrypted_backup.sql
```

---

## Contact Information

### Operations Team
- **Primary On-call**: ops@company.com
- **Secondary On-call**: backup-ops@company.com
- **Escalation Manager**: ops-manager@company.com

### Support Contacts
- **Development Team**: dev@company.com
- **Security Team**: security@company.com
- **Infrastructure Team**: infra@company.com

### External Resources
- **Vendor Support**: vendor-support@external.com
- **Cloud Provider**: cloud-support@provider.com
- **Monitoring Tools**: monitoring-support@tools.com

---

**Document Control**
- **Version**: 1.0.0
- **Last Reviewed**: 2025-12-29
- **Review Cycle**: Quarterly
- **Approval**: Operations Manager</content>
<parameter name="filePath">/home/dee/workspace/AI/Repo-Scanner/docs/operations_runbook.md