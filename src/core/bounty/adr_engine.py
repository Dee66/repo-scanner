"""Architecture Decision Records (ADR) Engine for Algora Bounty Hunting.

Analyzes repository ADR files to understand architectural decisions, constraints,
and trade-offs. Generates DECISIONS.md files that demonstrate senior architect
knowledge and provide interrogation defense.
"""

from typing import Dict, List, Optional, Any, Tuple
import os
import re
from pathlib import Path
import markdown
from datetime import datetime


class ADREngine:
    """Engine for analyzing and generating Architecture Decision Records."""

    def __init__(self):
        self.adr_patterns = [
            "docs/adr/",
            "docs/architecture/",
            "adr/",
            "architecture/",
            ".adr/",
            "decisions/"
        ]

        self.decision_patterns = {
            "constraint": re.compile(r"(?:constraint|limitation|trade.?off)", re.IGNORECASE),
            "alternative": re.compile(r"(?:alternative|considered|rejected)", re.IGNORECASE),
            "rationale": re.compile(r"(?:rationale|because|due to)", re.IGNORECASE),
            "impact": re.compile(r"(?:impact|effect|affect)", re.IGNORECASE)
        }

    def analyze_repository_adrs(self, repo_path: str) -> Dict[str, Any]:
        """Analyze all ADR files in a repository.

        Args:
            repo_path: Path to the repository root

        Returns:
            Dictionary containing ADR analysis results
        """
        adrs = []
        decisions = []

        for pattern in self.adr_patterns:
            adr_dir = Path(repo_path) / pattern
            if adr_dir.exists() and adr_dir.is_dir():
                for file_path in adr_dir.rglob("*.md"):
                    if file_path.is_file():
                        adr_content = self._parse_adr_file(file_path)
                        if adr_content:
                            adrs.append(adr_content)
                            decisions.extend(adr_content.get("decisions", []))

        return {
            "adr_files": adrs,
            "total_decisions": len(decisions),
            "decision_patterns": self._analyze_decision_patterns(decisions),
            "architectural_constraints": self._extract_constraints(decisions),
            "confidence_score": min(1.0, len(adrs) * 0.1 + len(decisions) * 0.05)
        }

    def generate_decisions_md(self, bounty_analysis: Dict, maintainer_profile: Dict) -> str:
        """Generate a DECISIONS.md file for a bounty PR.

        Args:
            bounty_analysis: Analysis results from bounty processing
            maintainer_profile: Maintainer's architectural preferences

        Returns:
            Content for DECISIONS.md file
        """
        decisions = []

        # Extract decisions from bounty analysis
        if "architecture_analysis" in bounty_analysis:
            arch_analysis = bounty_analysis["architecture_analysis"]
            decisions.extend(self._extract_bounty_decisions(arch_analysis))

        # Add maintainer-specific decisions
        maintainer_decisions = maintainer_profile.get("architecture_decisions", [])
        decisions.extend(maintainer_decisions)

        # Generate markdown content
        content = self._format_decisions_markdown(decisions, maintainer_profile)

        return content

    def validate_adr_compliance(self, implementation: Dict, adrs: List[Dict]) -> Dict[str, Any]:
        """Validate that implementation complies with ADR decisions.

        Args:
            implementation: Implementation details
            adrs: List of ADR documents

        Returns:
            Compliance validation results
        """
        violations = []
        compliances = []

        for adr in adrs:
            for decision in adr.get("decisions", []):
                compliance = self._check_decision_compliance(implementation, decision)
                if compliance["compliant"]:
                    compliances.append(compliance)
                else:
                    violations.append(compliance)

        return {
            "compliant": len(violations) == 0,
            "compliance_score": len(compliances) / max(1, len(compliances) + len(violations)),
            "violations": violations,
            "compliances": compliances
        }

    def _parse_adr_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a single ADR markdown file.

        Args:
            file_path: Path to the ADR file

        Returns:
            Parsed ADR content or None if parsing fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse markdown to extract structure
            html = markdown.markdown(content)
            # For now, use regex to extract sections
            # In a full implementation, use a proper markdown parser

            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else file_path.stem

            decisions = self._extract_decisions_from_content(content)

            return {
                "title": title,
                "file_path": str(file_path),
                "content": content,
                "decisions": decisions,
                "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }

        except Exception as e:
            print(f"Error parsing ADR file {file_path}: {e}")
            return None

    def _extract_decisions_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Extract architectural decisions from ADR content."""
        decisions = []

        # Split content into sections
        sections = re.split(r'^##\s+', content, flags=re.MULTILINE)

        for section in sections:
            if not section.strip():
                continue

            lines = section.split('\n')
            section_title = lines[0].strip()

            # Look for decision patterns
            decision_text = '\n'.join(lines[1:])

            if self._is_decision_section(section_title, decision_text):
                decision = {
                    "title": section_title,
                    "content": decision_text,
                    "type": self._classify_decision_type(decision_text),
                    "alternatives": self._extract_alternatives(decision_text),
                    "constraints": self._extract_constraints_from_text(decision_text),
                    "rationale": self._extract_rationale(decision_text)
                }
                decisions.append(decision)

        return decisions

    def _is_decision_section(self, title: str, content: str) -> bool:
        """Determine if a section contains architectural decisions."""
        decision_keywords = ["decision", "choice", "approach", "architecture", "design"]
        return any(keyword in title.lower() for keyword in decision_keywords) or \
               any(pattern.search(content) for pattern in self.decision_patterns.values())

    def _classify_decision_type(self, content: str) -> str:
        """Classify the type of architectural decision."""
        if "performance" in content.lower():
            return "performance"
        elif "security" in content.lower():
            return "security"
        elif "scalability" in content.lower():
            return "scalability"
        elif "maintainability" in content.lower():
            return "maintainability"
        else:
            return "architectural"

    def _extract_alternatives(self, content: str) -> List[str]:
        """Extract alternative approaches mentioned in the decision."""
        alternatives = []
        alt_match = re.search(r'alternatives?:?\s*\n?(.*?)(?:\n\n|\n##|\n#|\Z)',
                             content, re.DOTALL | re.IGNORECASE)
        if alt_match:
            alt_text = alt_match.group(1)
            # Split by bullets or numbers
            alternatives = re.split(r'[•\-\*]|\d+\.', alt_text)
            alternatives = [alt.strip() for alt in alternatives if alt.strip()]

        return alternatives

    def _extract_constraints_from_text(self, content: str) -> List[str]:
        """Extract constraints and trade-offs from decision text."""
        constraints = []
        constraint_match = re.search(r'constraints?:?\s*\n?(.*?)(?:\n\n|\n##|\n#|\Z)',
                                    content, re.DOTALL | re.IGNORECASE)
        if constraint_match:
            constraint_text = constraint_match.group(1)
            constraints = re.split(r'[•\-\*]|\d+\.', constraint_text)
            constraints = [c.strip() for c in constraints if c.strip()]

        return constraints

    def _extract_rationale(self, content: str) -> str:
        """Extract the rationale for the decision."""
        rationale_match = re.search(r'rationale:?\s*\n?(.*?)(?:\n\n|\n##|\n#|\Z)',
                                   content, re.DOTALL | re.IGNORECASE)
        return rationale_match.group(1).strip() if rationale_match else ""

    def _analyze_decision_patterns(self, decisions: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns in architectural decisions."""
        types = {}
        for decision in decisions:
            decision_type = decision.get("type", "unknown")
            types[decision_type] = types.get(decision_type, 0) + 1

        return {
            "decision_types": types,
            "avg_alternatives": sum(len(d.get("alternatives", [])) for d in decisions) / max(1, len(decisions)),
            "constraint_focus": any("constraint" in d.get("content", "").lower() for d in decisions)
        }

    def _extract_constraints(self, decisions: List[Dict]) -> List[str]:
        """Extract all architectural constraints from decisions."""
        constraints = []
        for decision in decisions:
            constraints.extend(decision.get("constraints", []))
        return list(set(constraints))  # Remove duplicates

    def _extract_bounty_decisions(self, arch_analysis: Dict) -> List[Dict]:
        """Extract architectural decisions from bounty analysis."""
        decisions = []

        # Example decisions based on analysis
        if "complexity_score" in arch_analysis:
            complexity = arch_analysis["complexity_score"]
            if complexity > 0.8:
                decisions.append({
                    "title": "Complexity Management",
                    "content": f"High complexity score ({complexity:.2f}) requires careful implementation",
                    "type": "maintainability",
                    "constraints": ["Must maintain readability", "Performance critical path"],
                    "rationale": "Balance between functionality and maintainability"
                })

        # Add more based on analysis data
        return decisions

    def _format_decisions_markdown(self, decisions: List[Dict], maintainer_profile: Dict) -> str:
        """Format decisions as markdown content."""
        content = ["# Architecture Decisions\n",
                  f"Generated for {maintainer_profile.get('name', 'Maintainer')} on {datetime.now().isoformat()}\n"]

        for i, decision in enumerate(decisions, 1):
            content.append(f"## Decision {i}: {decision['title']}\n")
            content.append(f"**Type:** {decision.get('type', 'architectural')}\n")

            if decision.get('rationale'):
                content.append(f"**Rationale:** {decision['rationale']}\n")

            if decision.get('alternatives'):
                content.append("**Alternatives Considered:**\n")
                for alt in decision['alternatives']:
                    content.append(f"- {alt}\n")
                content.append("\n")

            if decision.get('constraints'):
                content.append("**Constraints:**\n")
                for constraint in decision['constraints']:
                    content.append(f"- {constraint}\n")
                content.append("\n")

            content.append(f"{decision.get('content', '')}\n\n")

        return "".join(content)

    def _check_decision_compliance(self, implementation: Dict, decision: Dict) -> Dict[str, Any]:
        """Check if implementation complies with a specific decision."""
        # Simplified compliance check - in practice, this would be more sophisticated
        compliant = True
        issues = []

        # Check for constraint violations
        for constraint in decision.get("constraints", []):
            if constraint.lower() in str(implementation).lower():
                # This is a simplistic check - real implementation would parse implementation details
                pass
            else:
                compliant = False
                issues.append(f"Constraint not addressed: {constraint}")

        return {
            "decision": decision["title"],
            "compliant": compliant,
            "issues": issues
        }