"""Maintainer Profile Engine for Algora Bounty Hunting.

Analyzes repository patterns to build comprehensive maintainer preference profiles
for optimal bounty submission alignment.
"""

from typing import Dict, List, Set, Optional
from datetime import datetime
from .style_analyzer import StyleAnalyzer
from .adr_engine import ADREngine
from .historical_forensics import HistoricalForensicsEngine


class MaintainerProfileEngine:
    """Engine for analyzing and generating maintainer preference profiles."""

    def __init__(self):
        self.profile_cache = {}
        self.confidence_threshold = 0.8
        self.style_analyzer = StyleAnalyzer()
        self.adr_engine = ADREngine()
        self.forensics_engine = HistoricalForensicsEngine()

        # Hard-coded maintainer persona profiles
        self.persona_profiles = {
            "ziverge": self._get_ziverge_profile(),
            "golem": self._get_golem_profile()
        }

    def _get_ziverge_profile(self) -> Dict:
        """Ziverge profile: ZIO/ZIO-Blocks Scala expert."""
        return {
            "persona": "ziverge",
            "framework": "ZIO",
            "language": "Scala 3",
            "rules": {
                "strictly_functional": True,
                "no_var": True,
                "no_try_catch": True,
                "prefer_fold_over_match": True,
                "quiet_syntax": True,  # Scala 3 indentation-based
                "binary_compatibility": True  # Prefer final case class
            },
            "jargon_replacements": {
                "implemented": "wired up",
                "ensured": "guaranteed",
                "fixed": "patched",
                "added": "plugged in",
                "removed": "stripped out",
                "updated": "swapped",
                "optimized": "streamlined",
                "refactored": "restructured",
                "integrated": "meshed"
            },
            "code_style": {
                "imports": ["import zio._", "import zio.stream._"],
                "patterns": ["ZIO.succeed", "foldZIO", ".provide"],
                "avoid": ["var ", "try {", "catch {"]
            },
            "confidence": 0.95
        }

    def _get_golem_profile(self) -> Dict:
        """Golem profile: Rust/WASM expert."""
        return {
            "persona": "golem",
            "framework": "Rust/WASM",
            "language": "Rust",
            "rules": {
                "explicit_error_handling": True,
                "no_unwrap": True,
                "wit_adherence": True,  # WebAssembly Interface Type
                "zero_copy_operations": True,
                "avoid_unnecessary_allocations": True
            },
            "jargon_replacements": {
                "implemented": "forged",
                "ensured": "locked down",
                "fixed": "bolted",
                "added": "mounted",
                "removed": "unmounted",
                "updated": "retrofitted",
                "optimized": "tuned",
                "refactored": "reforged",
                "integrated": "fused"
            },
            "code_style": {
                "imports": ["use wasm_bindgen::prelude::*;", "use serde::{Serialize, Deserialize};"],
                "patterns": ["Result<T, E>", "#[wasm_bindgen]", "JsValue"],
                "avoid": [".unwrap()", ".expect(", "panic!("]
            },
            "confidence": 0.95
        }

    def generate_maintainer_profile(self, repository_url: str, intent_posture: Dict,
                                  governance: Dict, historical_data: Dict = None,
                                  forensics_data: Dict = None, style_data: Dict = None) -> Dict:
        """Generate a comprehensive maintainer preference profile."""
        # Handle None inputs safely
        intent_posture = intent_posture or {}
        governance = governance or {}
        historical_data = historical_data or {}
        forensics_data = forensics_data or {}
        style_data = style_data or {}

        # Extract repository identifier
        repo_id = self._extract_repo_id(repository_url)

        # Detect maintainer persona
        detected_persona = self._detect_maintainer_persona(repository_url, intent_posture, governance)

        # Build profile components
        code_style_preferences = self._analyze_code_style_preferences(intent_posture, governance)
        testing_requirements = self._analyze_testing_requirements(governance)
        documentation_standards = self._analyze_documentation_standards(governance)
        review_patterns = self._analyze_review_patterns(intent_posture, governance)
        communication_style = self._analyze_communication_style(intent_posture)

        # Apply persona-specific overrides if detected
        if detected_persona:
            code_style_preferences = self._apply_persona_overrides(code_style_preferences, detected_persona)
            communication_style = self._apply_persona_jargon(communication_style, detected_persona)

        # Incorporate historical data if available
        if historical_data:
            code_style_preferences = self._incorporate_historical_patterns(
                code_style_preferences, historical_data.get("code_style", {})
            )
            review_patterns = self._incorporate_historical_patterns(
                review_patterns, historical_data.get("review", {})
            )

        # Incorporate forensics data for enhanced profiling
        if forensics_data:
            code_style_preferences = self._incorporate_forensics_patterns(
                code_style_preferences, forensics_data
            )
            review_patterns = self._incorporate_forensics_review_patterns(
                review_patterns, forensics_data
            )
            communication_style = self._incorporate_forensics_communication(
                communication_style, forensics_data
            )

        # Incorporate style data for enhanced profiling
        if style_data:
            code_style_preferences = self._incorporate_style_patterns(
                code_style_preferences, style_data
            )

        # Calculate overall confidence
        profile_confidence = self._calculate_profile_confidence(
            code_style_preferences, testing_requirements, documentation_standards,
            review_patterns, communication_style
        )

        profile = {
            "repository_id": repo_id,
            "detected_persona": detected_persona,
            "code_style_preferences": code_style_preferences,
            "testing_requirements": testing_requirements,
            "documentation_standards": documentation_standards,
            "review_patterns": review_patterns,
            "communication_style": communication_style,
            "profile_confidence": profile_confidence,
            "generated_at": datetime.now().isoformat(),
            "profile_version": "2.0.0"  # Updated for persona support
        }

        # Cache profile for future use
        self.profile_cache[repo_id] = profile

        return profile

    def _detect_maintainer_persona(self, repository_url: str, intent_posture: Dict, governance: Dict) -> Optional[Dict]:
        """Detect specific maintainer persona based on repository characteristics."""
        repo_id = self._extract_repo_id(repository_url)

        # Check for Ziverge indicators (Scala/ZIO)
        if self._is_ziverge_repository(repo_id, intent_posture, governance):
            return self.persona_profiles["ziverge"]

        # Check for Golem indicators (Rust/WASM)
        if self._is_golem_repository(repo_id, intent_posture, governance):
            return self.persona_profiles["golem"]

        return None

    def _is_ziverge_repository(self, repo_id: str, intent_posture: Dict, governance: Dict) -> bool:
        """Check if repository matches Ziverge (Scala/ZIO) profile."""
        # Check repository name/owner for ZIO indicators
        if "zio" in repo_id.lower() or "scala" in repo_id.lower():
            return True

        # Check governance for Scala/ZIO patterns
        code_quality = governance.get("code_quality_governance", {})
        languages = str(code_quality.get("languages", [])).lower()
        if "scala" in languages and ("functional" in str(governance).lower() or "zio" in str(governance).lower()):
            return True

        # Check intent posture for functional programming indicators
        maturity_classification = intent_posture.get("maturity_classification", {}) or {}
        maturity = maturity_classification.get("paradigm", "")
        if "functional" in maturity.lower():
            return True

        return False

    def _is_golem_repository(self, repo_id: str, intent_posture: Dict, governance: Dict) -> bool:
        """Check if repository matches Golem (Rust/WASM) profile."""
        # Check repository name/owner for Rust/WASM indicators
        repo_lower = repo_id.lower()
        if "wasm" in repo_lower or "webassembly" in repo_lower or ("rust" in repo_lower and "wasm" in repo_lower):
            return True

        # Check governance for Rust/WASM patterns
        code_quality = governance.get("code_quality_governance", {})
        languages = str(code_quality.get("languages", [])).lower()
        if "rust" in languages and "wasm" in str(governance).lower():
            return True

        # Check for performance-critical indicators
        if "zero-copy" in str(governance).lower() or "webassembly" in str(governance).lower():
            return True

        return False

    def _apply_persona_overrides(self, code_style_preferences: Dict, persona: Dict) -> Dict:
        """Apply persona-specific code style overrides."""
        # Deep copy to avoid modifying original
        updated = code_style_preferences.copy()

        # Apply persona rules
        rules = persona.get("rules", {})
        if rules.get("strictly_functional"):
            updated["paradigm"] = "functional"
            updated["avoid_imperative"] = True

        if rules.get("no_var"):
            updated["allowed_keywords"] = updated.get("allowed_keywords", [])
            if "var" not in updated["allowed_keywords"]:
                updated["allowed_keywords"].append("no_var")

        if rules.get("explicit_error_handling"):
            updated["error_handling"] = "explicit"
            updated["avoid_unwrap"] = True

        # Apply code style patterns
        code_style = persona.get("code_style", {})
        if code_style.get("imports"):
            updated["preferred_imports"] = code_style["imports"]

        if code_style.get("patterns"):
            updated["required_patterns"] = code_style["patterns"]

        if code_style.get("avoid"):
            updated["avoided_patterns"] = code_style["avoid"]

        return updated

    def _apply_persona_jargon(self, communication_style: Dict, persona: Dict) -> Dict:
        """Apply persona-specific jargon replacements."""
        updated = communication_style.copy()
        updated["jargon_replacements"] = persona.get("jargon_replacements", {})
        return updated

    def _extract_repo_id(self, repository_url: str) -> str:
        """Extract repository identifier from URL."""
        # Handle various GitHub URL formats
        if "github.com" in repository_url:
            parts = repository_url.rstrip("/").split("/")
            if len(parts) >= 2:
                owner = parts[-2]
                repo = parts[-1].replace(".git", "")
                return f"github/{owner}/{repo}"
        return repository_url

    def _analyze_code_style_preferences(self, intent_posture: Dict, governance: Dict) -> Dict:
        """Analyze maintainer code style preferences."""
        preferences = {
            "formatting_tools": [],
            "linting_tools": [],
            "type_checking": False,
            "naming_conventions": "unknown",
            "code_structure_patterns": [],
            "confidence": 0.5
        }

        # Extract from governance signals
        code_quality = governance.get("code_quality_governance", {})
        preferences["formatting_tools"] = code_quality.get("formatters", [])
        preferences["linting_tools"] = code_quality.get("linters", [])
        preferences["type_checking"] = "mypy" in str(code_quality.get("static_analyzers", []))

        # Analyze intent posture for structural preferences
        maturity_classification = intent_posture.get("maturity_classification", {}) or {}
        maturity = maturity_classification.get("maturity_level", "unknown")
        if maturity in ["stable", "mature"]:
            preferences["code_structure_patterns"].append("modular_architecture")
            preferences["confidence"] = 0.8
        elif maturity in ["experimental", "alpha"]:
            preferences["code_structure_patterns"].append("flexible_structure")
            preferences["confidence"] = 0.6

        # Analyze semantic patterns for naming conventions
        code_patterns = intent_posture.get("code_patterns", {})
        if "snake_case" in str(code_patterns).lower():
            preferences["naming_conventions"] = "snake_case"
        elif "camelCase" in str(code_patterns).lower():
            preferences["naming_conventions"] = "camelCase"

        return preferences

    def _analyze_testing_requirements(self, governance: Dict) -> Dict:
        """Analyze maintainer testing requirements and preferences."""
        requirements = {
            "required_coverage": "unknown",
            "testing_frameworks": [],
            "test_structure": "unknown",
            "ci_integration": False,
            "confidence": 0.5
        }

        # Check CI/CD governance for testing requirements
        ci_cd = governance.get("ci_cd_governance", {})
        if ci_cd.get("ci_platforms") or ci_cd.get("test_commands"):
            requirements["ci_integration"] = True
            requirements["confidence"] = 0.8

        # Analyze test signals (would be passed from test_signal_analysis)
        # This is a placeholder for integration with test_signal_analysis.py
        requirements["testing_frameworks"] = ["pytest", "unittest"]  # Default assumption

        return requirements

    def _analyze_documentation_standards(self, governance: Dict) -> Dict:
        """Analyze maintainer documentation standards."""
        standards = {
            "readme_required": True,
            "docstring_style": "unknown",
            "api_documentation": False,
            "changelog_required": False,
            "confidence": 0.5
        }

        # Check documentation governance
        docs = governance.get("documentation_governance", {})
        if docs.get("readme_files"):
            standards["readme_required"] = True
            standards["confidence"] = 0.7

        if docs.get("api_docs"):
            standards["api_documentation"] = True

        return standards

    def _analyze_review_patterns(self, intent_posture: Dict, governance: Dict) -> Dict:
        """Analyze maintainer code review patterns and preferences."""
        patterns = {
            "review_depth": "standard",
            "approval_requirements": "single_approver",
            "focus_areas": [],
            "response_time": "unknown",
            "confidence": 0.5
        }

        # Infer from maturity and governance
        maturity_classification = intent_posture.get("maturity_classification", {}) or {}
        maturity = maturity_classification.get("maturity_level", "unknown")
        if maturity in ["stable", "mature"]:
            patterns["review_depth"] = "thorough"
            patterns["approval_requirements"] = "multiple_approvers"
            patterns["focus_areas"] = ["stability", "backward_compatibility", "testing"]
            patterns["confidence"] = 0.8
        elif maturity in ["experimental", "alpha"]:
            patterns["review_depth"] = "flexible"
            patterns["approval_requirements"] = "single_approver"
            patterns["focus_areas"] = ["innovation", "functionality"]
            patterns["confidence"] = 0.6

        return patterns

    def _analyze_communication_style(self, intent_posture: Dict) -> Dict:
        """Analyze maintainer communication style preferences."""
        if not intent_posture:
            return {
                "tone": "professional",
                "detail_level": "standard",
                "response_pattern": "responsive",
                "feedback_style": "constructive",
                "confidence": 0.5
            }

        style = {
            "tone": "professional",
            "detail_level": "standard",
            "response_pattern": "responsive",
            "feedback_style": "constructive",
            "confidence": 0.5
        }

        # Infer from repository characteristics
        maturity_classification = intent_posture.get("maturity_classification", {}) or {}
        maturity = maturity_classification.get("maturity_level", "unknown")
        if maturity in ["stable", "mature"]:
            style["tone"] = "formal"
            style["detail_level"] = "comprehensive"
            style["confidence"] = 0.7
        elif maturity in ["experimental", "alpha"]:
            style["tone"] = "collaborative"
            style["detail_level"] = "concise"
            style["confidence"] = 0.6

        return style

    def _incorporate_historical_patterns(self, current_patterns: Dict,
                                       historical_patterns: Dict) -> Dict:
        """Incorporate historical data to refine patterns."""
        if not historical_patterns:
            return current_patterns

        # Blend current analysis with historical data
        blended = current_patterns.copy()

        # Update confidence based on historical validation
        historical_confidence = historical_patterns.get("validation_accuracy", 0.5)
        current_confidence = current_patterns.get("confidence", 0.5)
        blended["confidence"] = (current_confidence + historical_confidence) / 2

        # Incorporate validated patterns
        if "validated_preferences" in historical_patterns:
            validated = historical_patterns["validated_preferences"]
            for key, value in validated.items():
                if key in blended:
                    blended[key] = value  # Override with validated data

        return blended

    def _calculate_profile_confidence(self, *components) -> float:
        """Calculate overall confidence in the maintainer profile."""
        confidences = []
        for component in components:
            if isinstance(component, dict) and "confidence" in component:
                confidences.append(component["confidence"])

        if not confidences:
            return 0.5

        # Use harmonic mean for conservative confidence estimation
        if all(c > 0 for c in confidences):
            harmonic_mean = len(confidences) / sum(1/c for c in confidences)
            return harmonic_mean

        return sum(confidences) / len(confidences)

    def get_profile(self, repository_url: str) -> Optional[Dict]:
        """Retrieve cached maintainer profile."""
        repo_id = self._extract_repo_id(repository_url)
        return self.profile_cache.get(repo_id)

    def update_profile(self, repository_url: str, updates: Dict) -> None:
        """Update maintainer profile with new information."""
        repo_id = self._extract_repo_id(repository_url)
        if repo_id in self.profile_cache:
            self.profile_cache[repo_id].update(updates)
            self.profile_cache[repo_id]["updated_at"] = datetime.now().isoformat()

    def _incorporate_forensics_patterns(self, code_style: Dict, forensics_data: Dict) -> Dict:
        """Incorporate forensics data into code style preferences."""
        enhanced_style = code_style.copy()

        # Use commit style analysis from forensics
        commit_patterns = forensics_data.get("commit_patterns", {})
        if commit_patterns:
            # Update import style based on conventional commits ratio
            conventional_ratio = commit_patterns.get("conventional_commits_ratio", 0)
            if conventional_ratio > 0.7:
                enhanced_style["commit_style"] = "conventional"
            elif conventional_ratio < 0.3:
                enhanced_style["commit_style"] = "freeform"

            # Update emoji usage preference
            emoji_ratio = commit_patterns.get("emoji_usage_ratio", 0)
            enhanced_style["emoji_in_commits"] = emoji_ratio > 0.2

        # Use code churn patterns
        code_churn = forensics_data.get("code_churn", {})
        if code_churn.get("total_lines", 0) > 10000:  # Large codebase
            enhanced_style["large_codebase"] = True
            enhanced_style["prefer_incremental_changes"] = True

        return enhanced_style

    def _incorporate_style_patterns(self, code_style: Dict, style_data: Dict) -> Dict:
        """Incorporate style analysis data into code style preferences."""
        enhanced_style = code_style.copy()

        # Incorporate import hygiene preferences
        import_hygiene = style_data.get("import_hygiene", {})
        if import_hygiene:
            grouping = import_hygiene.get("import_grouping")
            if grouping == "separated":
                enhanced_style["import_grouping"] = "separated"
                enhanced_style["blank_lines_between_imports"] = True
            elif grouping == "mixed":
                enhanced_style["import_grouping"] = "mixed"

            preference = import_hygiene.get("import_preference", {})
            if preference.get("stdlib_ratio", 0) > 0.5:
                enhanced_style["prefer_stdlib"] = True
            if preference.get("local_ratio", 0) > 0.3:
                enhanced_style["frequent_local_imports"] = True

        # Incorporate code grafting patterns
        code_grafting = style_data.get("code_grafting", {})
        if code_grafting:
            func_naming = code_grafting.get("function_naming")
            if func_naming == "prefers_private":
                enhanced_style["prefer_private_functions"] = True

            documentation = code_grafting.get("documentation")
            if documentation == "well_documented":
                enhanced_style["require_docstrings"] = True
            elif documentation == "minimal":
                enhanced_style["minimal_documentation"] = True

            class_naming = code_grafting.get("class_naming")
            if class_naming == "pascal_case":
                enhanced_style["class_naming"] = "pascal_case"

        return enhanced_style

    def _incorporate_forensics_review_patterns(self, review_patterns: Dict, forensics_data: Dict) -> Dict:
        """Incorporate forensics data into review pattern analysis."""
        enhanced_patterns = review_patterns.copy()

        # Use merge patterns to infer review requirements
        merge_patterns = forensics_data.get("merge_patterns", {})
        avg_merge_time = merge_patterns.get("avg_merge_time_hours", 0)

        if avg_merge_time > 48:  # Long review cycles
            enhanced_patterns["thorough_reviews"] = True
            enhanced_patterns["requires_detailed_testing"] = True
        elif avg_merge_time < 2:  # Fast reviews
            enhanced_patterns["fast_iterations"] = True

        # Use reviewer patterns
        reviewer_patterns = forensics_data.get("reviewer_patterns", {})
        if reviewer_patterns.get("avg_review_time", 0) > 24:
            enhanced_patterns["requires_comprehensive_docs"] = True

        return enhanced_patterns

    def _incorporate_forensics_communication(self, communication_style: Dict, forensics_data: Dict) -> Dict:
        """Incorporate forensics data into communication style analysis."""
        enhanced_style = communication_style.copy()

        # Use commit message patterns
        commit_patterns = forensics_data.get("commit_patterns") or {}
        avg_length = commit_patterns.get("avg_message_length", 50)

        if avg_length < 30:
            enhanced_style["detail_level"] = "concise"
        elif avg_length > 80:
            enhanced_style["detail_level"] = "comprehensive"
        else:
            enhanced_style["detail_level"] = "standard"

        # Use technical decision patterns
        technical_decisions = forensics_data.get("technical_decisions") or []
        if technical_decisions:
            enhanced_style["technical_depth"] = "deep"
            enhanced_style["prefers_architecture_discussions"] = True

        return enhanced_style


def generate_maintainer_profile(repository_url: str, intent_posture: Dict,
                              governance: Dict, historical_data: Dict = None,
                              forensics_data: Dict = None, style_data: Dict = None) -> Dict:
    """Convenience function for generating maintainer profiles."""
    engine = MaintainerProfileEngine()
    return engine.generate_maintainer_profile(repository_url, intent_posture,
                                            governance, historical_data, forensics_data, style_data)