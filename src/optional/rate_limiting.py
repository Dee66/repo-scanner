"""Advanced rate limiting and abuse prevention system."""

import time
import threading
import ipaddress
import re
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict, deque
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

# Optional imports
try:
    from .logging_aggregation import setup_structured_logging
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False

try:
    from .alerting import get_alert_manager
    ALERTING_AVAILABLE = True
except ImportError:
    ALERTING_AVAILABLE = False

class RateLimitRule:
    """Represents a rate limiting rule."""

    def __init__(self, name: str, max_requests: int, window_seconds: int,
                 block_duration_seconds: int = 0, description: str = ""):
        self.name = name
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.block_duration_seconds = block_duration_seconds
        self.description = description

    def __repr__(self):
        return f"RateLimitRule({self.name}: {self.max_requests}/{self.window_seconds}s)"

class AbusePreventionEngine:
    """Advanced abuse prevention and rate limiting engine."""

    def __init__(self):
        if LOGGING_AVAILABLE:
            self.logger = setup_structured_logging("abuse_prevention")
        else:
            import logging
            self.logger = logging.getLogger(__name__)

        # Rate limiting storage
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.blocked_ips: Dict[str, float] = {}  # IP -> unblock timestamp
        self.suspicious_ips: Set[str] = set()
        self.rate_limit_rules: Dict[str, RateLimitRule] = {}

        # Abuse detection
        self.failed_attempts: Dict[str, List[float]] = defaultdict(list)
        self.suspicious_patterns: Dict[str, re.Pattern] = {}
        self.user_agent_blacklist: Set[str] = set()
        self.ip_whitelist: Set[str] = set()
        self.ip_blacklist: Set[str] = set()

        # Configuration
        self.max_concurrent_requests = 10
        self.active_requests: Dict[str, int] = defaultdict(int)
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        self.suspicious_request_threshold = 5  # Failed attempts before marking suspicious

        # Load default rules
        self._load_default_rules()

        # Thread safety
        self.lock = threading.RLock()

    def _load_default_rules(self):
        """Load default rate limiting rules."""
        self.rate_limit_rules = {
            'api_general': RateLimitRule(
                'api_general', 100, 60, 300,
                'General API rate limit: 100 requests per minute, 5min block'
            ),
            'api_scan': RateLimitRule(
                'api_scan', 5, 300, 1800,
                'Scan endpoint: 5 requests per 5 minutes, 30min block'
            ),
            'api_health': RateLimitRule(
                'api_health', 30, 60, 0,
                'Health checks: 30 requests per minute, no block'
            ),
            'dashboard': RateLimitRule(
                'dashboard', 200, 60, 60,
                'Dashboard access: 200 requests per minute, 1min block'
            ),
        }

        # Suspicious patterns
        self.suspicious_patterns = {
            'sql_injection': re.compile(r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC)\b', re.IGNORECASE),
            'path_traversal': re.compile(r'\.\./|\.\.\\'),
            'command_injection': re.compile(r'[;&|`$()]'),
            'xss_attempt': re.compile(r'<script|<iframe|<object|<embed', re.IGNORECASE),
            'scanner_abuse': re.compile(r'(nmap|nikto|dirbuster|sqlmap|nessus)', re.IGNORECASE),
        }

        # Default blacklisted user agents
        self.user_agent_blacklist = {
            'sqlmap', 'nikto', 'dirbuster', 'gobuster', 'masscan', 'zmap',
            'nessus', 'acunetix', 'openvas', 'qualys', 'rapid7', 'metasploit'
        }

    def check_rate_limit(self, identifier: str, rule_name: str = 'api_general') -> Tuple[bool, Optional[float]]:
        """
        Check if request should be rate limited.

        Returns:
            (allowed: bool, retry_after: Optional[float])
        """
        with self.lock:
            # Check if IP is blocked
            if identifier in self.blocked_ips:
                unblock_time = self.blocked_ips[identifier]
                if time.time() < unblock_time:
                    return False, unblock_time - time.time()
                else:
                    # Unblock expired
                    del self.blocked_ips[identifier]

            # Check if IP is blacklisted
            if identifier in self.ip_blacklist:
                return False, None

            # Check whitelist (always allow)
            if identifier in self.ip_whitelist:
                return True, None

            # Get rule
            rule = self.rate_limit_rules.get(rule_name, self.rate_limit_rules['api_general'])
            if not rule:
                return True, None

            # Clean old requests
            now = time.time()
            request_times = self.request_history[identifier]
            while request_times and now - request_times[0] > rule.window_seconds:
                request_times.popleft()

            # Check rate limit
            if len(request_times) >= rule.max_requests:
                if rule.block_duration_seconds > 0:
                    self.blocked_ips[identifier] = now + rule.block_duration_seconds
                    self.logger.warning(f"IP {identifier} blocked for {rule.block_duration_seconds}s (rate limit exceeded)")

                    # Report security event for rate limit violations
                    try:
                        from .security_incident_response import report_security_event, IncidentSeverity
                        report_security_event(
                            event_type="rate_limit_exceeded",
                            severity=IncidentSeverity.MEDIUM,
                            source_ip=identifier,
                            endpoint=rule_name,
                            description=f"Rate limit exceeded for rule {rule_name}: {len(request_times)} requests in {rule.window_seconds}s",
                            raw_data={"rule": rule_name, "request_count": len(request_times), "limit": rule.max_requests}
                        )
                    except ImportError:
                        pass  # Incident response not available

                return False, rule.window_seconds

            # Add current request
            request_times.append(now)
            return True, None

    def check_concurrent_requests(self, identifier: str) -> bool:
        """Check if concurrent request limit is exceeded."""
        with self.lock:
            current = self.active_requests[identifier]
            if current >= self.max_concurrent_requests:
                return False
            self.active_requests[identifier] = current + 1
            return True

    def release_concurrent_request(self, identifier: str):
        """Release a concurrent request slot."""
        with self.lock:
            if self.active_requests[identifier] > 0:
                self.active_requests[identifier] -= 1

    def check_request_size(self, size: int) -> bool:
        """Check if request size is within limits."""
        return size <= self.max_request_size

    def analyze_request(self, ip: str, user_agent: str, path: str, body: str = "") -> Dict[str, any]:
        """
        Analyze request for suspicious activity.

        Returns:
            Dict with analysis results
        """
        analysis = {
            'suspicious': False,
            'reasons': [],
            'risk_score': 0,
            'actions': []
        }

        # Check user agent
        if user_agent and any(ua.lower() in user_agent.lower() for ua in self.user_agent_blacklist):
            analysis['suspicious'] = True
            analysis['reasons'].append('blacklisted_user_agent')
            analysis['risk_score'] += 50

        # Check suspicious patterns in path and body
        check_text = f"{path} {body}"
        for pattern_name, pattern in self.suspicious_patterns.items():
            if pattern.search(check_text):
                analysis['suspicious'] = True
                analysis['reasons'].append(f'suspicious_pattern_{pattern_name}')
                analysis['risk_score'] += 20

                # Report security event for suspicious patterns
                try:
                    from .security_incident_response import report_security_event, IncidentSeverity
                    severity = IncidentSeverity.CRITICAL if pattern_name in ['sql_injection', 'command_injection'] else IncidentSeverity.HIGH
                    report_security_event(
                        event_type=f"suspicious_pattern_{pattern_name}",
                        severity=severity,
                        source_ip=ip,
                        user_agent=user_agent,
                        endpoint=path,
                        description=f"Suspicious pattern detected: {pattern_name}",
                        raw_data={"pattern": pattern_name, "matched_text": check_text[:100]}
                    )
                except ImportError:
                    pass  # Incident response not available

        # Check for rapid failed attempts
        failed_times = self.failed_attempts[ip]
        now = time.time()
        # Clean old failures (last hour)
        failed_times[:] = [t for t in failed_times if now - t < 3600]

        if len(failed_times) >= self.suspicious_request_threshold:
            analysis['suspicious'] = True
            analysis['reasons'].append('rapid_failed_attempts')
            analysis['risk_score'] += 30

        # Determine actions based on risk score
        if analysis['risk_score'] >= 80:
            analysis['actions'].append('block_ip')
        elif analysis['risk_score'] >= 50:
            analysis['actions'].append('rate_limit_aggressive')
        elif analysis['risk_score'] >= 20:
            analysis['actions'].append('log_suspicious')

        return analysis

    def record_failed_attempt(self, ip: str):
        """Record a failed authentication or validation attempt."""
        with self.lock:
            self.failed_attempts[ip].append(time.time())

            # Check if IP should be marked suspicious
            failed_times = self.failed_attempts[ip]
            now = time.time()
            recent_failures = [t for t in failed_times if now - t < 300]  # Last 5 minutes

            if len(recent_failures) >= self.suspicious_request_threshold:
                self.suspicious_ips.add(ip)
                self.logger.warning(f"IP {ip} marked as suspicious ({len(recent_failures)} failures in 5 minutes)")

                # Report security event
                try:
                    from .security_incident_response import report_security_event, IncidentSeverity
                    report_security_event(
                        event_type="failed_authentication",
                        severity=IncidentSeverity.MEDIUM,
                        source_ip=ip,
                        description=f"Rapid failed attempts detected: {len(recent_failures)} failures in 5 minutes",
                        raw_data={"failure_count": len(recent_failures), "time_window": 300}
                    )
                except ImportError:
                    pass  # Incident response not available

    def is_ip_suspicious(self, ip: str) -> bool:
        """Check if IP is marked as suspicious."""
        return ip in self.suspicious_ips

    def add_to_blacklist(self, ip: str, reason: str = "manual"):
        """Add IP to blacklist."""
        with self.lock:
            self.ip_blacklist.add(ip)
            self.logger.warning(f"IP {ip} added to blacklist (reason: {reason})")

    def remove_from_blacklist(self, ip: str):
        """Remove IP from blacklist."""
        with self.lock:
            self.ip_blacklist.discard(ip)
            self.logger.info(f"IP {ip} removed from blacklist")

    def add_to_whitelist(self, ip: str, reason: str = "manual"):
        """Add IP to whitelist."""
        with self.lock:
            self.ip_whitelist.add(ip)
            self.logger.info(f"IP {ip} added to whitelist (reason: {reason})")

    def get_stats(self) -> Dict[str, any]:
        """Get abuse prevention statistics."""
        with self.lock:
            return {
                'blocked_ips': len(self.blocked_ips),
                'suspicious_ips': len(self.suspicious_ips),
                'blacklisted_ips': len(self.ip_blacklist),
                'whitelisted_ips': len(self.ip_whitelist),
                'active_requests': dict(self.active_requests),
                'total_request_history': sum(len(history) for history in self.request_history.values()),
                'failed_attempts': {ip: len(times) for ip, times in self.failed_attempts.items()},
            }

    def cleanup_expired_blocks(self):
        """Clean up expired IP blocks."""
        with self.lock:
            now = time.time()
            expired = [ip for ip, unblock_time in self.blocked_ips.items() if now >= unblock_time]
            for ip in expired:
                del self.blocked_ips[ip]
            if expired:
                self.logger.info(f"Cleaned up {len(expired)} expired IP blocks")

    def save_state(self, filepath: str):
        """Save abuse prevention state to file."""
        try:
            state = {
                'blocked_ips': self.blocked_ips,
                'suspicious_ips': list(self.suspicious_ips),
                'ip_blacklist': list(self.ip_blacklist),
                'ip_whitelist': list(self.ip_whitelist),
                'failed_attempts': dict(self.failed_attempts),
                'saved_at': time.time()
            }
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2)
            self.logger.info(f"Abuse prevention state saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save abuse prevention state: {e}")

    def load_state(self, filepath: str):
        """Load abuse prevention state from file."""
        try:
            if not os.path.exists(filepath):
                return

            with open(filepath, 'r') as f:
                state = json.load(f)

            self.blocked_ips = state.get('blocked_ips', {})
            self.suspicious_ips = set(state.get('suspicious_ips', []))
            self.ip_blacklist = set(state.get('ip_blacklist', []))
            self.ip_whitelist = set(state.get('ip_whitelist', []))
            self.failed_attempts = defaultdict(list, state.get('failed_attempts', {}))

            self.logger.info(f"Abuse prevention state loaded from {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to load abuse prevention state: {e}")

class ProgressiveDelay:
    """Implements progressive delays for suspicious activity."""

    def __init__(self):
        self.delays = [0, 1, 5, 15, 30, 60]  # Seconds
        self.ip_violation_counts: Dict[str, int] = {}
        self.lock = threading.RLock()

    def get_delay(self, ip: str) -> float:
        """Get delay for IP based on violation history."""
        with self.lock:
            count = self.ip_violation_counts.get(ip, 0)
            if count >= len(self.delays):
                return self.delays[-1]
            return self.delays[count]

    def record_violation(self, ip: str):
        """Record a violation for IP."""
        with self.lock:
            self.ip_violation_counts[ip] = self.ip_violation_counts.get(ip, 0) + 1

    def reset_violations(self, ip: str):
        """Reset violation count for IP."""
        with self.lock:
            self.ip_violation_counts[ip] = 0

# Global instances
_abuse_engine = None
_progressive_delay = None

def get_abuse_prevention_engine() -> AbusePreventionEngine:
    """Get the global abuse prevention engine instance."""
    global _abuse_engine
    if _abuse_engine is None:
        _abuse_engine = AbusePreventionEngine()
    return _abuse_engine

def get_progressive_delay() -> ProgressiveDelay:
    """Get the global progressive delay instance."""
    global _progressive_delay
    if _progressive_delay is None:
        _progressive_delay = ProgressiveDelay()
    return _progressive_delay