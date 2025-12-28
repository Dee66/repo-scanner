"""
Security Incident Response System for Repository Scanner

This module provides comprehensive security incident response procedures including:
- Automated detection and alerting for security events
- Incident classification and prioritization
- Automated response actions
- Integration with existing alerting and logging systems
- Incident tracking and reporting
"""

import time
import threading
import json
import logging
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import os
import hashlib

logger = logging.getLogger(__name__)

class IncidentSeverity(Enum):
    """Security incident severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IncidentStatus(Enum):
    """Security incident status."""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"

class IncidentType(Enum):
    """Types of security incidents."""
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    PATH_TRAVERSAL = "path_traversal"
    MALICIOUS_SCANNING = "malicious_scanning"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_EXFILTRATION = "data_exfiltration"
    DOS_ATTACK = "dos_attack"
    MALWARE_INFECTION = "malware_infection"
    CONFIGURATION_VIOLATION = "configuration_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

@dataclass
class SecurityEvent:
    """Represents a security event."""
    event_id: str
    timestamp: float
    event_type: str
    severity: IncidentSeverity
    source_ip: str
    user_agent: str
    endpoint: str
    description: str
    raw_data: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None

@dataclass
class SecurityIncident:
    """Represents a security incident."""
    incident_id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    incident_type: IncidentType
    created_at: float
    updated_at: float
    source_ip: str
    affected_endpoints: Set[str] = field(default_factory=set)
    events: List[SecurityEvent] = field(default_factory=list)
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    automated_actions_taken: List[str] = field(default_factory=list)
    manual_actions_required: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)

class IncidentResponseRule:
    """Rule for automated incident response."""

    def __init__(self, name: str, incident_type: IncidentType, severity: IncidentSeverity,
                 conditions: List[Callable], actions: List[Callable],
                 cooldown_seconds: int = 300, description: str = ""):
        self.name = name
        self.incident_type = incident_type
        self.severity = severity
        self.conditions = conditions
        self.actions = actions
        self.cooldown_seconds = cooldown_seconds
        self.description = description
        self.last_triggered = 0

    def should_trigger(self, event: SecurityEvent) -> bool:
        """Check if this rule should trigger for the given event."""
        if time.time() - self.last_triggered < self.cooldown_seconds:
            return False

        return all(condition(event) for condition in self.conditions)

    def execute_actions(self, incident: SecurityIncident) -> List[str]:
        """Execute automated actions for this incident."""
        executed_actions = []
        for action in self.actions:
            try:
                result = action(incident)
                if result:
                    executed_actions.append(result)
            except Exception as e:
                logger.error(f"Error executing action for rule {self.name}: {e}")

        if executed_actions:
            self.last_triggered = time.time()

        return executed_actions

class SecurityIncidentResponse:
    """Main security incident response system."""

    def __init__(self):
        self.incidents: Dict[str, SecurityIncident] = {}
        self.active_incidents: Dict[str, SecurityIncident] = {}
        self.response_rules: List[IncidentResponseRule] = []
        self.event_buffer: List[SecurityEvent] = []
        self.incident_counter = 0
        self._lock = threading.RLock()

        # Optional integrations
        self._alerting_available = self._check_alerting_available()
        self._logging_available = self._check_logging_available()

        # Load default response rules
        self._load_default_rules()

        # Start background processing
        self._running = False
        self._processor_thread: Optional[threading.Thread] = None
        self._start_background_processor()

    def _check_alerting_available(self) -> bool:
        """Check if alerting system is available."""
        try:
            from .alerting import get_alert_manager
            return True
        except ImportError:
            return False

    def _check_logging_available(self) -> bool:
        """Check if structured logging is available."""
        try:
            from .logging_aggregation import setup_structured_logging
            return True
        except ImportError:
            return False

    def _load_default_rules(self):
        """Load default incident response rules."""

        # Brute force attack response
        def brute_force_condition(event: SecurityEvent) -> bool:
            return (event.event_type == "failed_authentication" and
                    "rapid_failures" in event.raw_data)

        def block_ip_action(incident: SecurityIncident) -> str:
            try:
                from .rate_limiting import get_abuse_prevention_engine
                engine = get_abuse_prevention_engine()
                engine.add_to_blacklist(incident.source_ip, f"incident_{incident.incident_id}")
                return f"Blocked IP {incident.source_ip}"
            except Exception as e:
                logger.error(f"Failed to block IP: {e}")
                return ""

        # SQL injection response
        def sql_injection_condition(event: SecurityEvent) -> bool:
            return (event.event_type == "suspicious_pattern" and
                    event.raw_data.get("pattern_type") == "sql_injection")

        def log_security_alert_action(incident: SecurityIncident) -> str:
            if self._alerting_available:
                try:
                    from .alerting import get_alert_manager, AlertSeverity
                    alert_manager = get_alert_manager()
                    alert_manager.create_alert(
                        name=f"Security Incident: {incident.title}",
                        description=incident.description,
                        severity=AlertSeverity.CRITICAL if incident.severity == IncidentSeverity.CRITICAL else AlertSeverity.HIGH,
                        labels={"incident_id": incident.incident_id, "type": incident.incident_type.value}
                    )
                    return "Security alert created"
                except Exception as e:
                    logger.error(f"Failed to create alert: {e}")
            return ""

        # High severity incident escalation
        def high_severity_condition(event: SecurityEvent) -> bool:
            return event.severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]

        def escalate_incident_action(incident: SecurityIncident) -> str:
            incident.manual_actions_required.append("Immediate security team review required")
            incident.tags.add("escalated")
            return "Incident escalated for manual review"

        # Add rules
        self.response_rules.extend([
            IncidentResponseRule(
                name="brute_force_block",
                incident_type=IncidentType.BRUTE_FORCE,
                severity=IncidentSeverity.HIGH,
                conditions=[brute_force_condition],
                actions=[block_ip_action, log_security_alert_action],
                description="Block IPs involved in brute force attacks"
            ),
            IncidentResponseRule(
                name="sql_injection_alert",
                incident_type=IncidentType.SQL_INJECTION,
                severity=IncidentSeverity.CRITICAL,
                conditions=[sql_injection_condition],
                actions=[log_security_alert_action, escalate_incident_action],
                description="Alert and escalate SQL injection attempts"
            ),
            IncidentResponseRule(
                name="high_severity_escalation",
                incident_type=IncidentType.SUSPICIOUS_ACTIVITY,
                severity=IncidentSeverity.HIGH,
                conditions=[high_severity_condition],
                actions=[escalate_incident_action],
                description="Escalate high severity incidents"
            )
        ])

    def _start_background_processor(self):
        """Start background incident processor."""
        self._running = True
        self._processor_thread = threading.Thread(target=self._process_events, daemon=True)
        self._processor_thread.start()

    def _process_events(self):
        """Background processor for security events."""
        while self._running:
            try:
                # Process buffered events
                events_to_process = []
                with self._lock:
                    if self.event_buffer:
                        events_to_process = self.event_buffer[:]
                        self.event_buffer.clear()

                for event in events_to_process:
                    self._process_security_event(event)

                # Clean up old incidents (keep last 30 days)
                self._cleanup_old_incidents()

                time.sleep(1)  # Process every second

            except Exception as e:
                logger.error(f"Error in incident processor: {e}")
                time.sleep(5)

    def _process_security_event(self, event: SecurityEvent):
        """Process a single security event."""
        # Check if this event should create or update an incident
        incident = self._find_or_create_incident(event)

        if incident:
            # Add event to incident
            incident.events.append(event)
            incident.updated_at = time.time()
            incident.affected_endpoints.add(event.endpoint)

            # Check response rules
            for rule in self.response_rules:
                if rule.should_trigger(event):
                    actions_taken = rule.execute_actions(incident)
                    incident.automated_actions_taken.extend(actions_taken)

            # Update incident status based on severity and actions
            self._update_incident_status(incident)

            logger.warning(f"Security incident updated: {incident.incident_id} - {incident.title}")

    def _find_or_create_incident(self, event: SecurityEvent) -> Optional[SecurityIncident]:
        """Find existing incident or create new one for the event."""
        # Look for existing incident with same IP and type in last hour
        cutoff_time = time.time() - 3600

        for incident in self.active_incidents.values():
            if (incident.source_ip == event.source_ip and
                incident.incident_type.value == event.event_type and
                incident.created_at > cutoff_time):
                return incident

        # Create new incident
        self.incident_counter += 1
        incident_id = f"SEC-{int(time.time())}-{self.incident_counter:04d}"

        incident_type = self._classify_incident_type(event)
        severity = self._assess_severity(event)

        incident = SecurityIncident(
            incident_id=incident_id,
            title=f"{incident_type.value.replace('_', ' ').title()} from {event.source_ip}",
            description=event.description,
            severity=severity,
            status=IncidentStatus.DETECTED,
            incident_type=incident_type,
            created_at=time.time(),
            updated_at=time.time(),
            source_ip=event.source_ip
        )

        self.incidents[incident_id] = incident
        self.active_incidents[incident_id] = incident

        return incident

    def _classify_incident_type(self, event: SecurityEvent) -> IncidentType:
        """Classify the incident type based on the event."""
        event_type_mapping = {
            "failed_authentication": IncidentType.BRUTE_FORCE,
            "suspicious_pattern_sql_injection": IncidentType.SQL_INJECTION,
            "suspicious_pattern_xss": IncidentType.XSS_ATTACK,
            "suspicious_pattern_path_traversal": IncidentType.PATH_TRAVERSAL,
            "malicious_scanning": IncidentType.MALICIOUS_SCANNING,
            "rate_limit_exceeded": IncidentType.DOS_ATTACK,
            "unauthorized_access": IncidentType.UNAUTHORIZED_ACCESS,
        }

        return event_type_mapping.get(event.event_type, IncidentType.SUSPICIOUS_ACTIVITY)

    def _assess_severity(self, event: SecurityEvent) -> IncidentSeverity:
        """Assess the severity of the incident."""
        # High severity for critical patterns
        if event.severity == IncidentSeverity.CRITICAL:
            return IncidentSeverity.CRITICAL

        # Medium to high for specific attack types
        if event.event_type in ["suspicious_pattern_sql_injection", "suspicious_pattern_xss"]:
            return IncidentSeverity.HIGH

        # Medium for other suspicious activities
        if "suspicious" in event.event_type:
            return IncidentSeverity.MEDIUM

        return IncidentSeverity.LOW

    def _update_incident_status(self, incident: SecurityIncident):
        """Update incident status based on current state."""
        # Auto-resolve low severity incidents after some time
        if (incident.severity == IncidentSeverity.LOW and
            time.time() - incident.created_at > 3600):  # 1 hour
            incident.status = IncidentStatus.RESOLVED
            incident.resolution_notes = "Auto-resolved: Low severity incident"
            if incident.incident_id in self.active_incidents:
                del self.active_incidents[incident.incident_id]

        # Escalate critical incidents
        elif incident.severity == IncidentSeverity.CRITICAL:
            incident.status = IncidentStatus.INVESTIGATING
            if "escalated" not in incident.tags:
                incident.tags.add("escalated")

    def _cleanup_old_incidents(self):
        """Clean up old resolved incidents."""
        cutoff_time = time.time() - (30 * 24 * 3600)  # 30 days
        incidents_to_remove = []

        for incident_id, incident in self.incidents.items():
            if (incident.status in [IncidentStatus.RESOLVED, IncidentStatus.FALSE_POSITIVE] and
                incident.updated_at < cutoff_time):
                incidents_to_remove.append(incident_id)

        for incident_id in incidents_to_remove:
            del self.incidents[incident_id]

    def report_security_event(self, event_type: str, severity: IncidentSeverity,
                            source_ip: str, user_agent: str = "", endpoint: str = "",
                            description: str = "", raw_data: Dict[str, Any] = None,
                            correlation_id: Optional[str] = None) -> str:
        """Report a security event for processing."""
        event_id = hashlib.md5(f"{time.time()}_{source_ip}_{event_type}".encode()).hexdigest()[:16]

        event = SecurityEvent(
            event_id=event_id,
            timestamp=time.time(),
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            user_agent=user_agent,
            endpoint=endpoint,
            description=description,
            raw_data=raw_data or {},
            correlation_id=correlation_id
        )

        with self._lock:
            self.event_buffer.append(event)

        return event_id

    def get_incident(self, incident_id: str) -> Optional[SecurityIncident]:
        """Get incident by ID."""
        return self.incidents.get(incident_id)

    def get_active_incidents(self) -> Dict[str, SecurityIncident]:
        """Get all active incidents."""
        with self._lock:
            return dict(self.active_incidents)

    def update_incident_status(self, incident_id: str, status: IncidentStatus,
                             notes: str = "", assigned_to: str = None) -> bool:
        """Update incident status."""
        incident = self.incidents.get(incident_id)
        if not incident:
            return False

        incident.status = status
        incident.updated_at = time.time()
        if notes:
            incident.resolution_notes = notes
        if assigned_to:
            incident.assigned_to = assigned_to

        # Remove from active if resolved
        if status in [IncidentStatus.RESOLVED, IncidentStatus.FALSE_POSITIVE]:
            self.active_incidents.pop(incident_id, None)

        return True

    def get_incident_stats(self) -> Dict[str, Any]:
        """Get incident statistics."""
        with self._lock:
            total_incidents = len(self.incidents)
            active_incidents = len(self.active_incidents)

            severity_counts = {}
            type_counts = {}
            status_counts = {}

            for incident in self.incidents.values():
                severity_counts[incident.severity.value] = severity_counts.get(incident.severity.value, 0) + 1
                type_counts[incident.incident_type.value] = type_counts.get(incident.incident_type.value, 0) + 1
                status_counts[incident.status.value] = status_counts.get(incident.status.value, 0) + 1

            return {
                "total_incidents": total_incidents,
                "active_incidents": active_incidents,
                "severity_breakdown": severity_counts,
                "type_breakdown": type_counts,
                "status_breakdown": status_counts,
                "response_rules_count": len(self.response_rules)
            }

    def shutdown(self):
        """Shutdown the incident response system."""
        self._running = False
        if self._processor_thread:
            self._processor_thread.join(timeout=5)

# Global instance
_incident_response: Optional[SecurityIncidentResponse] = None

def get_incident_response() -> SecurityIncidentResponse:
    """Get the global incident response instance."""
    global _incident_response
    if _incident_response is None:
        _incident_response = SecurityIncidentResponse()
    return _incident_response

def report_security_event(event_type: str, severity: IncidentSeverity,
                        source_ip: str, **kwargs) -> str:
    """Convenience function to report security events."""
    return get_incident_response().report_security_event(event_type, severity, source_ip, **kwargs)