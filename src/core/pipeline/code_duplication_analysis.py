#!/usr/bin/env python3
"""
Code Duplication Analysis Stage

Analyzes code for duplication, clones, and copy-paste patterns that indicate
maintenance issues, technical debt, and potential refactoring opportunities.
"""

import hashlib
import re
from collections import defaultdict
from typing import Dict, List, Any, Set, Tuple
from pathlib import Path

import logging

logger = logging.getLogger(__name__)

class CodeDuplicationAnalyzer:
    """Analyzes code for duplication and clone detection."""

    def __init__(self):
        self.min_block_size = 6  # Minimum lines for a code block
        self.min_clone_length = 10  # Minimum characters for clone detection
        self.similarity_threshold = 0.8  # Similarity threshold for clone detection

    def analyze_code_duplication(self, file_list: List[str], semantic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive code duplication analysis.

        Args:
            file_list: List of files to analyze
            semantic_data: Semantic analysis results

        Returns:
            Dict containing code duplication analysis results
        """
        logger.info("Starting code duplication analysis")

        duplication_results = {
            "total_files_analyzed": 0,
            "total_lines_analyzed": 0,
            "duplicate_blocks": [],
            "clone_groups": [],
            "duplication_metrics": {
                "duplicate_line_ratio": 0.0,
                "duplicate_block_count": 0,
                "largest_clone_group": 0,
                "most_duplicated_file": ""
            },
            "duplication_score": 100,  # Lower is better (less duplication)
            "recommendations": [],
            "severity_breakdown": {
                "critical": 0,  # >50% duplication
                "high": 0,      # 30-50% duplication
                "medium": 0,    # 15-30% duplication
                "low": 0        # <15% duplication
            }
        }

        # Filter to code files only
        code_files = self._filter_code_files(file_list)

        if not code_files:
            duplication_results["recommendations"].append("No code files found for duplication analysis")
            return duplication_results

        # Extract code blocks from all files
        file_blocks = {}
        for file_path in code_files:
            try:
                blocks = self._extract_code_blocks(file_path)
                if blocks:
                    file_blocks[file_path] = blocks
                    duplication_results["total_lines_analyzed"] += sum(len(block.split('\n')) for block in blocks)
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")

        duplication_results["total_files_analyzed"] = len(file_blocks)

        # Find duplicate blocks
        duplicates = self._find_duplicate_blocks(file_blocks)
        duplication_results["duplicate_blocks"] = duplicates

        # Group into clone families
        clone_groups = self._group_into_clones(duplicates)
        duplication_results["clone_groups"] = clone_groups

        # Calculate metrics
        duplication_results["duplication_metrics"] = self._calculate_duplication_metrics(
            file_blocks, duplicates, clone_groups
        )

        # Calculate duplication score
        duplication_results["duplication_score"] = self._calculate_duplication_score(
            duplication_results["duplication_metrics"]
        )

        # Categorize by severity
        duplication_results["severity_breakdown"] = self._categorize_by_severity(file_blocks, duplicates)

        # Generate recommendations
        duplication_results["recommendations"] = self._generate_duplication_recommendations(
            duplication_results
        )

        return duplication_results

    def _filter_code_files(self, file_list: List[str]) -> List[str]:
        """Filter to include only code files."""
        code_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.clj'
        }

        code_files = []
        for file_path in file_list:
            if any(file_path.endswith(ext) for ext in code_extensions):
                # Skip test files, generated files, and minified files
                if not self._is_excluded_file(file_path):
                    code_files.append(file_path)

        return code_files

    def _is_excluded_file(self, file_path: str) -> bool:
        """Check if file should be excluded from duplication analysis."""
        excluded_patterns = [
            '/test/', '/tests/', '/spec/', '/specs/',
            '.test.', '.spec.', '.min.', '.generated.',
            '/node_modules/', '/build/', '/dist/', '/target/',
            '/__pycache__/', '.pyc', '/venv/', '/env/'
        ]

        file_lower = file_path.lower()
        return any(pattern in file_lower for pattern in excluded_patterns)

    def _extract_code_blocks(self, file_path: str) -> List[str]:
        """Extract meaningful code blocks from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return []

        # Split into lines
        lines = content.split('\n')

        # Remove comments and empty lines for block extraction
        code_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not self._is_comment_line(stripped, file_path):
                code_lines.append(line)

        if len(code_lines) < self.min_block_size:
            return []

        # Extract sliding windows of code blocks
        blocks = []
        for i in range(len(code_lines) - self.min_block_size + 1):
            block = '\n'.join(code_lines[i:i + self.min_block_size])
            if len(block) >= self.min_clone_length:
                blocks.append(block)

        return blocks

    def _is_comment_line(self, line: str, file_path: str) -> bool:
        """Check if a line is a comment."""
        if file_path.endswith('.py'):
            return line.startswith('#')
        elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.cs', '.php', '.go', '.rs')):
            return line.startswith('//') or line.startswith('/*') or '*/' in line
        elif file_path.endswith('.rb'):
            return line.startswith('#')
        elif file_path.endswith(('.html', '.xml')):
            return line.strip().startswith('<!--')
        return False

    def _find_duplicate_blocks(self, file_blocks: Dict[str, List[str]]) -> List[Dict]:
        """Find duplicate code blocks across files."""
        block_occurrences = defaultdict(list)

        # Count occurrences of each block
        for file_path, blocks in file_blocks.items():
            for i, block in enumerate(blocks):
                # Normalize whitespace for comparison
                normalized_block = self._normalize_code_block(block)
                block_hash = hashlib.md5(normalized_block.encode()).hexdigest()
                block_occurrences[block_hash].append({
                    'file': file_path,
                    'block_index': i,
                    'original_block': block,
                    'normalized_block': normalized_block
                })

        # Find duplicates (blocks that appear in multiple files or multiple times in same file)
        duplicates = []
        for block_hash, occurrences in block_occurrences.items():
            if len(occurrences) > 1:
                # Calculate similarity between occurrences
                similar_groups = self._group_similar_occurrences(occurrences)
                for group in similar_groups:
                    if len(group) > 1:
                        duplicates.append({
                            'block_hash': block_hash,
                            'occurrences': group,
                            'duplicate_count': len(group),
                            'estimated_lines': len(group[0]['original_block'].split('\n'))
                        })

        return duplicates

    def _normalize_code_block(self, block: str) -> str:
        """Normalize code block for comparison."""
        # Remove extra whitespace, normalize indentation
        lines = []
        for line in block.split('\n'):
            # Remove leading/trailing whitespace
            stripped = line.strip()
            if stripped:
                # Normalize indentation to 4 spaces
                indent = len(line) - len(line.lstrip())
                normalized_indent = (indent // 4) * 4  # Round to nearest 4 spaces
                lines.append(' ' * normalized_indent + stripped)

        return '\n'.join(lines)

    def _group_similar_occurrences(self, occurrences: List[Dict]) -> List[List[Dict]]:
        """Group similar occurrences based on content similarity."""
        if len(occurrences) <= 1:
            return [occurrences]

        # Simple grouping: all occurrences with same normalized content
        groups = []
        used = set()

        for i, occ1 in enumerate(occurrences):
            if i in used:
                continue

            group = [occ1]
            used.add(i)

            for j, occ2 in enumerate(occurrences):
                if j not in used and self._calculate_similarity(occ1['normalized_block'], occ2['normalized_block']) >= self.similarity_threshold:
                    group.append(occ2)
                    used.add(j)

            if len(group) > 1:
                groups.append(group)

        return groups

    def _calculate_similarity(self, block1: str, block2: str) -> float:
        """Calculate similarity between two code blocks."""
        # Simple token-based similarity
        tokens1 = self._tokenize_code(block1)
        tokens2 = self._tokenize_code(block2)

        if not tokens1 or not tokens2:
            return 0.0

        # Jaccard similarity
        set1 = set(tokens1)
        set2 = set(tokens2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _tokenize_code(self, code: str) -> List[str]:
        """Simple tokenization of code."""
        # Split on whitespace and punctuation
        tokens = re.findall(r'\w+|[^\w\s]', code)
        return [token.lower() for token in tokens if len(token) > 1]

    def _group_into_clones(self, duplicates: List[Dict]) -> List[Dict]:
        """Group duplicate blocks into clone families."""
        clone_groups = []

        for duplicate in duplicates:
            clone_groups.append({
                'clone_id': f"clone_{len(clone_groups)}",
                'block_hash': duplicate['block_hash'],
                'occurrences': duplicate['occurrences'],
                'total_occurrences': duplicate['duplicate_count'],
                'estimated_lines': duplicate['estimated_lines'],
                'files_affected': len(set(occ['file'] for occ in duplicate['occurrences']))
            })

        return clone_groups

    def _calculate_duplication_metrics(self, file_blocks: Dict[str, List[str]],
                                     duplicates: List[Dict], clone_groups: List[Dict]) -> Dict[str, Any]:
        """Calculate duplication metrics."""
        total_duplicate_blocks = sum(d['duplicate_count'] for d in duplicates)
        total_lines = sum(len(blocks) for blocks in file_blocks.values())

        # Calculate duplicate line ratio
        duplicate_line_ratio = (total_duplicate_blocks * self.min_block_size) / total_lines if total_lines > 0 else 0

        # Find largest clone group
        largest_clone = max((cg['total_occurrences'] for cg in clone_groups), default=0)

        # Find most duplicated file
        file_duplication_count = defaultdict(int)
        for duplicate in duplicates:
            for occ in duplicate['occurrences']:
                file_duplication_count[occ['file']] += 1

        most_duplicated_file = max(file_duplication_count.items(), key=lambda x: x[1], default=("", 0))[0]

        return {
            "duplicate_line_ratio": round(duplicate_line_ratio, 3),
            "duplicate_block_count": total_duplicate_blocks,
            "largest_clone_group": largest_clone,
            "most_duplicated_file": most_duplicated_file
        }

    def _calculate_duplication_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate duplication score (lower is better)."""
        base_score = 100

        # Deduct points based on duplicate line ratio
        ratio_penalty = metrics["duplicate_line_ratio"] * 100  # Convert to percentage
        base_score -= min(ratio_penalty, 50)

        # Deduct points for large clone groups
        clone_penalty = min(metrics["largest_clone_group"] * 2, 20)
        base_score -= clone_penalty

        return max(0, base_score)

    def _categorize_by_severity(self, file_blocks: Dict[str, List[str]], duplicates: List[Dict]) -> Dict[str, int]:
        """Categorize files by duplication severity."""
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        # Calculate duplication ratio per file
        file_duplicate_lines = defaultdict(int)

        for duplicate in duplicates:
            for occ in duplicate['occurrences']:
                file_duplicate_lines[occ['file']] += duplicate['estimated_lines']

        for file_path, total_lines in file_blocks.items():
            duplicate_lines = file_duplicate_lines[file_path]
            total_file_lines = len(total_lines) * self.min_block_size  # Approximate

            if total_file_lines > 0:
                ratio = duplicate_lines / total_file_lines

                if ratio > 0.5:
                    severity_counts["critical"] += 1
                elif ratio > 0.3:
                    severity_counts["high"] += 1
                elif ratio > 0.15:
                    severity_counts["medium"] += 1
                else:
                    severity_counts["low"] += 1

        return severity_counts

    def _generate_duplication_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on duplication analysis."""
        recommendations = []

        metrics = results["duplication_metrics"]
        severity = results["severity_breakdown"]

        if metrics["duplicate_line_ratio"] > 0.3:
            recommendations.append(f"High code duplication detected ({metrics['duplicate_line_ratio']:.1%} of code). Consider refactoring.")

        if metrics["largest_clone_group"] > 5:
            recommendations.append(f"Large clone group with {metrics['largest_clone_group']} occurrences found. Extract common functionality.")

        if severity["critical"] > 0:
            recommendations.append(f"{severity['critical']} files have critical duplication (>50%). Immediate refactoring needed.")

        if severity["high"] > 0:
            recommendations.append(f"{severity['high']} files have high duplication (30-50%). Refactoring recommended.")

        if results["duplication_score"] < 70:
            recommendations.append("Overall code duplication is high. Implement duplication detection in CI/CD pipeline.")

        if not recommendations:
            recommendations.append("Code duplication levels are acceptable.")

        return recommendations


def analyze_code_duplication(file_list: List[str], semantic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze code for duplication and clone detection.

    Args:
        file_list: List of files to analyze
        semantic_data: Semantic analysis results

    Returns:
        Dict containing code duplication analysis results
    """
    analyzer = CodeDuplicationAnalyzer()
    return analyzer.analyze_code_duplication(file_list, semantic_data)
