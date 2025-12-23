#!/usr/bin/env python3
"""
Code Comprehension Analysis Stage

Uses AI models to understand code patterns, intent, and potential issues.
Integrates with the AI inference pipeline for offline operation.
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ...performance_optimizer import get_performance_optimizer

from ...ai.inference_pipeline import get_ai_pipeline
from ..static_semantic_analysis import analyze_semantic_structure

logger = logging.getLogger(__name__)

@dataclass
class CodeUnderstanding:
    """Understanding of a code file or component."""
    file_path: str
    summary: str
    intent: str
    complexity: str
    patterns: List[str]
    potential_issues: List[str]
    confidence: float

@dataclass
class ComprehensionResult:
    """Result of code comprehension analysis."""
    overall_summary: str
    key_components: List[CodeUnderstanding]
    architecture_patterns: List[str]
    quality_assessment: Dict[str, Any]
    risk_indicators: List[str]

class CodeComprehensionAnalyzer:
    """Analyzes code using AI models for deep understanding."""

    def __init__(self, registry_path: Optional[Path] = None):
        self.ai_pipeline = get_ai_pipeline(registry_path)
        # Use the latest trained lightweight models
        self.summarization_model = "lightweight-summarization-1766516780"  # Latest summarization model
        self.classification_model = "lightweight-classification-1766516788"  # Latest classification model
        self.performance_optimizer = get_performance_optimizer()

    def analyze_code_comprehension(self, repository_path: Path, semantic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive code comprehension analysis.

        Args:
            repository_path: Path to the repository
            semantic_data: Results from semantic analysis

        Returns:
            Dict containing comprehension analysis results
        """
        logger.info("Starting code comprehension analysis")

        # Memory optimization before heavy AI processing
        initial_memory = self.performance_optimizer.get_memory_usage()
        logger.info(f"Code comprehension - Initial memory: {initial_memory['rss_mb']:.1f}MB")

        try:
            # Extract code files from semantic data
            code_files = self._extract_code_files(semantic_data)

            # Analyze individual files with batch processing for performance
            file_understandings = []
            batch_size = 5  # Process files in batches to optimize AI inference

            for i in range(0, min(len(code_files), 10), batch_size):  # Limit to first 10 files
                batch = code_files[i:i + batch_size]
                batch_understandings = self._analyze_file_batch(batch, repository_path)
                file_understandings.extend(batch_understandings)

            # Synthesize overall comprehension
            comprehension = self._synthesize_comprehension(file_understandings, semantic_data)

            return {
                "comprehension_analysis": {
                    "overall_summary": comprehension.overall_summary,
                    "key_components": [
                        {
                            "file_path": u.file_path,
                            "summary": u.summary,
                            "intent": u.intent,
                            "complexity": u.complexity,
                            "patterns": u.patterns,
                            "potential_issues": u.potential_issues,
                            "confidence": u.confidence
                        } for u in comprehension.key_components
                    ],
                    "architecture_patterns": comprehension.architecture_patterns,
                    "quality_assessment": comprehension.quality_assessment,
                    "risk_indicators": comprehension.risk_indicators
                },
                "analysis_metadata": {
                    "files_analyzed": len(file_understandings),
                    "total_files_available": len(code_files),
                    "ai_models_used": self._get_available_models(),
                    "analysis_timestamp": "2025-12-23T00:00:00Z"
                }
            }

            # Memory optimization after processing
            self.performance_optimizer.optimize_memory()
            final_memory = self.performance_optimizer.get_memory_usage()
            memory_delta = final_memory['rss_mb'] - initial_memory['rss_mb']
            logger.info(f"Code comprehension completed - Memory delta: {memory_delta:.1f}MB")

            return {
                "comprehension_analysis": {
                    "overall_summary": comprehension.overall_summary,
                    "key_components": [
                        {
                            "file_path": u.file_path,
                            "summary": u.summary,
                            "intent": u.intent,
                            "complexity": u.complexity,
                            "patterns": u.patterns,
                            "potential_issues": u.potential_issues,
                            "confidence": u.confidence
                        } for u in comprehension.key_components
                    ],
                    "architecture_patterns": comprehension.architecture_patterns,
                    "quality_assessment": comprehension.quality_assessment,
                    "risk_indicators": comprehension.risk_indicators
                },
                "analysis_metadata": {
                    "files_analyzed": len(file_understandings),
                    "total_files_available": len(code_files),
                    "ai_models_used": self._get_available_models(),
                    "analysis_timestamp": "2025-12-23T00:00:00Z"
                }
            }

        except Exception as e:
            logger.error(f"Code comprehension analysis failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "comprehension_analysis": {
                    "error": str(e),
                    "overall_summary": "Analysis failed due to technical issues",
                    "key_components": [],
                    "architecture_patterns": [],
                    "quality_assessment": {},
                    "risk_indicators": ["Analysis infrastructure not available"]
                },
                "analysis_metadata": {
                    "files_analyzed": 0,
                    "total_files_available": 0,
                    "ai_models_used": [],
                    "analysis_timestamp": "2025-12-23T00:00:00Z"
                }
            }

    def _extract_code_files(self, semantic_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract code files from semantic analysis data."""
        code_files = []

        # Python files
        if "python_analysis" in semantic_data:
            python_data = semantic_data["python_analysis"]
            for module in python_data.get("modules", []):
                code_files.append({
                    "path": module,
                    "language": "python",
                    "type": "module"
                })

        # JavaScript files
        if "javascript_analysis" in semantic_data:
            js_data = semantic_data["javascript_analysis"]
            for module in js_data.get("modules", []):
                code_files.append({
                    "path": module,
                    "language": "javascript",
                    "type": "module"
                })

        # TypeScript files
        if "typescript_analysis" in semantic_data:
            ts_data = semantic_data["typescript_analysis"]
            for module in ts_data.get("modules", []):
                code_files.append({
                    "path": module,
                    "language": "typescript",
                    "type": "module"
                })

        # Java files
        if "java_analysis" in semantic_data:
            java_data = semantic_data["java_analysis"]
            for module in java_data.get("modules", []):
                code_files.append({
                    "path": module,
                    "language": "java",
                    "type": "module"
                })

        return code_files

    def _analyze_file_batch(self, file_batch: List[Dict[str, Any]], repo_path: Path) -> List[Optional[CodeUnderstanding]]:
        """Analyze a batch of files using optimized AI inference."""
        understandings = []

        # Prepare batch data for AI processing
        batch_contents = []
        valid_files = []

        for file_info in file_batch:
            file_path = repo_path / file_info["path"]
            if not file_path.exists():
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if content.strip():
                    batch_contents.append(content[:1000])  # Limit content size
                    valid_files.append(file_info)
            except Exception as e:
                logger.warning(f"Failed to read file {file_path}: {e}")

        if not batch_contents:
            return []

        # Batch AI inference for better performance
        try:
            # Batch summarization
            summaries = self._batch_generate_summaries(batch_contents)

            # Batch intent classification
            intents = self._batch_classify_intents(batch_contents)

            # Process results
            for i, (file_info, content) in enumerate(zip(valid_files, batch_contents)):
                summary = summaries[i] if i < len(summaries) else "Code file summary"
                intent = intents[i] if i < len(intents) else "application_code"

                patterns = self._identify_patterns(content)
                issues = self._detect_issues(content)
                complexity = self._assess_complexity(content)

                understandings.append(CodeUnderstanding(
                    file_path=file_info["path"],
                    summary=summary,
                    intent=intent,
                    complexity=complexity,
                    patterns=patterns,
                    potential_issues=issues,
                    confidence=0.8
                ))

        except Exception as e:
            logger.warning(f"Batch analysis failed, falling back to individual processing: {e}")
            # Fallback to individual processing
            for file_info in file_batch:
                understanding = self._analyze_file(file_info, repo_path)
                if understanding:
                    understandings.append(understanding)

        return understandings

    def _batch_generate_summaries(self, contents: List[str]) -> List[str]:
        """Generate summaries for a batch of content using async processing."""
        try:
            # Use asyncio to run batch inference
            async def _async_batch_summaries():
                input_batch = [
                    {
                        "task": "summarize",
                        "content": content
                    } for content in contents
                ]
                results = await self.ai_pipeline.infer_batch_async(
                    self.summarization_model, input_batch
                )
                return results

            # Run async batch processing
            results = asyncio.run(_async_batch_summaries())

            summaries = []
            for result in results:
                if isinstance(result, Exception):
                    summaries.append("Code file summary")
                elif result and "generated_text" in result.output:
                    summaries.append(result.output["generated_text"])
                else:
                    summaries.append("Code file summary")

            return summaries

        except Exception as e:
            logger.warning(f"Async batch summarization failed, using sync fallback: {e}")
            # Fallback to sync processing
            return self._batch_generate_summaries_sync(contents)

    def _batch_generate_summaries_sync(self, contents: List[str]) -> List[str]:
        """Sync fallback for batch summarization."""
        summaries = []
        for content in contents:
            try:
                result = self.ai_pipeline.infer(
                    self.summarization_model,
                    {
                        "task": "summarize",
                        "content": content
                    }
                )
                if result and "generated_text" in result.output:
                    summaries.append(result.output["generated_text"])
                else:
                    summaries.append("Code file summary")
            except Exception:
                summaries.append("Code file summary")
        return summaries

    def _batch_classify_intents(self, contents: List[str]) -> List[str]:
        """Classify intents for a batch of content using async processing."""
        try:
            async def _async_batch_intents():
                input_batch = [
                    {
                        "task": "classify",
                        "content": content
                    } for content in contents
                ]
                results = await self.ai_pipeline.infer_batch_async(
                    self.classification_model, input_batch
                )
                return results

            results = asyncio.run(_async_batch_intents())

            intents = []
            for result in results:
                if isinstance(result, Exception):
                    intents.append("application_code")
                elif result and "classification" in result.output:
                    intents.append(result.output["classification"])
                else:
                    intents.append("application_code")

            return intents

        except Exception as e:
            logger.warning(f"Async batch classification failed, using sync fallback: {e}")
            return self._batch_classify_intents_sync(contents)

    def _batch_classify_intents_sync(self, contents: List[str]) -> List[str]:
        """Sync fallback for batch intent classification."""
        intents = []
        for content in contents:
            try:
                result = self.ai_pipeline.infer(
                    self.classification_model,
                    {
                        "task": "classify",
                        "content": content
                    }
                )
                if result and "classification" in result.output:
                    intents.append(result.output["classification"])
                else:
                    intents.append("application_code")
            except Exception:
                intents.append("application_code")
        return intents

    def _analyze_file(self, file_info: Dict[str, Any], repo_path: Path) -> Optional[CodeUnderstanding]:
        """Analyze a single file using AI models."""
        file_path = repo_path / file_info["path"]

        if not file_path.exists():
            return None

        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if not content.strip():
                return None

            # Use AI models for analysis
            summary = self._generate_summary(content)
            intent = self._classify_intent(content)
            patterns = self._identify_patterns(content)
            issues = self._detect_issues(content)

            # Estimate complexity
            complexity = self._assess_complexity(content)

            return CodeUnderstanding(
                file_path=file_info["path"],
                summary=summary,
                intent=intent,
                complexity=complexity,
                patterns=patterns,
                potential_issues=issues,
                confidence=0.8  # Placeholder confidence
            )

        except Exception as e:
            logger.warning(f"Failed to analyze file {file_path}: {e}")
            return None

    def _generate_summary(self, content: str) -> str:
        """Generate a summary of the code using AI or fallback."""
        try:
            # Try to use AI model
            result = self.ai_pipeline.infer(
                self.summarization_model,
                {
                    "task": "summarize",
                    "content": content[:2000]  # Limit content size
                }
            )
            if result and "generated_text" in result.output:
                return result.output["generated_text"]
        except Exception:
            pass

        # Fallback to basic analysis
        lines = content.split('\n')
        functions = content.count('def ')
        classes = content.count('class ')
        return f"Code file with {len(lines)} lines containing {functions} functions and {classes} classes"

    def _classify_intent(self, content: str) -> str:
        """Classify the intent/purpose of the code."""
        try:
            result = self.ai_pipeline.infer(
                self.classification_model,
                {
                    "task": "classify",
                    "content": content[:1000]
                }
            )
            if result and "generated_text" in result.output:
                return result.output["generated_text"]
        except Exception:
            pass

        # Fallback classification
        if "def main" in content or "if __name__ == '__main__'" in content:
            return "Main application entry point"
        elif "class" in content and "def __init__" in content:
            return "Object-oriented implementation"
        elif "import" in content and "def" in content:
            return "Utility functions and imports"
        else:
            return "General code implementation"

    def _identify_patterns(self, content: str) -> List[str]:
        """Identify code patterns and architectural elements."""
        patterns = []

        # Basic pattern detection
        if "class" in content:
            patterns.append("Object-oriented design")
        if "def" in content and "@" in content:
            patterns.append("Decorator usage")
        if "async def" in content:
            patterns.append("Asynchronous programming")
        if "import" in content and "from" in content:
            patterns.append("Modular imports")
        if "try:" in content and "except" in content:
            patterns.append("Error handling")
        if "with" in content:
            patterns.append("Context management")

        return patterns

    def _detect_issues(self, content: str) -> List[str]:
        """Detect potential issues in the code."""
        issues = []

        # Basic issue detection
        if len(content) > 10000:
            issues.append("Large file - consider splitting into smaller modules")
        if content.count("TODO") > 0:
            issues.append("Contains TODO comments")
        if "print(" in content and "logging" not in content:
            issues.append("Using print statements instead of logging")
        if "except:" in content and "Exception" not in content:
            issues.append("Broad exception handling")
        if "eval(" in content or "exec(" in content:
            issues.append("Use of eval/exec - security risk")

        return issues

    def _assess_complexity(self, content: str) -> str:
        """Assess code complexity."""
        lines = len(content.split('\n'))
        functions = content.count('def ')
        classes = content.count('class ')

        if lines > 500 or (functions + classes) > 20:
            return "High complexity"
        elif lines > 200 or (functions + classes) > 10:
            return "Medium complexity"
        else:
            return "Low complexity"

    def _synthesize_comprehension(self, file_understandings: List[CodeUnderstanding],
                                semantic_data: Dict[str, Any]) -> ComprehensionResult:
        """Synthesize overall comprehension from individual file analyses."""
        try:
            if not file_understandings:
                return ComprehensionResult(
                    overall_summary="No code files could be analyzed",
                    key_components=[],
                    architecture_patterns=[],
                    quality_assessment={},
                    risk_indicators=["No analyzable code found"]
                )

            # Aggregate patterns
            all_patterns = []
            for understanding in file_understandings:
                all_patterns.extend(understanding.patterns)

            # Find most common patterns
            pattern_counts = {}
            for pattern in all_patterns:
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

            architecture_patterns = sorted(
                [(p, c) for p, c in pattern_counts.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]  # Top 5 patterns

            # Aggregate issues
            all_issues = []
            for understanding in file_understandings:
                all_issues.extend(understanding.potential_issues)

            # Quality assessment
            quality_assessment = {
                "code_maturity": self._assess_maturity(file_understandings),
                "architecture_consistency": len(architecture_patterns) > 2,
                "issue_density": len(all_issues) / len(file_understandings) if file_understandings else 0,
                "pattern_diversity": len(set(all_patterns))
            }

            # Overall summary
            summary = self._generate_overall_summary(file_understandings, architecture_patterns)

            return ComprehensionResult(
                overall_summary=summary,
                key_components=file_understandings,
                architecture_patterns=[p[0] for p in architecture_patterns],
                quality_assessment=quality_assessment,
                risk_indicators=all_issues[:10]  # Limit to top 10 issues
            )
        except Exception as e:
            # Fallback in case of any issues
            return ComprehensionResult(
                overall_summary=f"Analysis failed: {str(e)}",
                key_components=[],
                architecture_patterns=[],
                quality_assessment={},
                risk_indicators=["Analysis error"]
            )

    def _assess_maturity(self, understandings: List[CodeUnderstanding]) -> str:
        """Assess overall code maturity based on file analyses."""
        high_complexity = sum(1 for u in understandings if u.complexity == "High complexity")
        total_files = len(understandings)

        if total_files == 0:
            return "No files to assess"

        ratio = high_complexity / total_files
        if ratio > 0.5:
            return "Complex codebase - may need refactoring"
        elif ratio > 0.2:
            return "Moderately mature with some complexity"
        else:
            return "Well-structured and maintainable"

    def _generate_overall_summary(self, understandings: List[CodeUnderstanding],
                                patterns: List[tuple]) -> str:
        """Generate overall summary of the codebase."""
        total_files = len(understandings)
        main_patterns = [p[0] for p in patterns[:3]]

        summary = f"Codebase with {total_files} analyzed files. "

        if main_patterns:
            summary += f"Main architectural patterns: {', '.join(main_patterns)}. "

        # Add maturity assessment
        maturity = self._assess_maturity(understandings)
        summary += f"Overall assessment: {maturity}."

        return summary

    def _get_available_models(self) -> List[str]:
        """Get list of available AI models."""
        try:
            return self.ai_pipeline.get_available_models()
        except Exception:
            return []

def analyze_code_comprehension(repository_path: Path, semantic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for code comprehension analysis.

    Args:
        repository_path: Path to the repository
        semantic_data: Semantic analysis results

    Returns:
        Dict containing comprehension analysis results
    """
    analyzer = CodeComprehensionAnalyzer()
    return analyzer.analyze_code_comprehension(repository_path, semantic_data)