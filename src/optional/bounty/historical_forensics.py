"""Historical Forensics Engine for Algora Bounty Hunting.

Analyzes git history to extract technical decisions, PR patterns, and contextual
anchors that demonstrate deep repository knowledge. Provides evidence of
long-term institutional knowledge to avoid AI detection.
"""

from typing import Dict, List, Optional, Any, Tuple
import os
from pathlib import Path
from datetime import datetime, timedelta
import re
from collections import defaultdict, Counter
import git
from git import Repo


class HistoricalForensicsEngine:
    """Engine for analyzing git history and extracting forensic evidence."""

    def __init__(self):
        self.repo_cache = {}  # Cache for repository analysis
        self.patterns = {
            "technical_decision": re.compile(r"(?:decided|chose|opted|went with|using)", re.IGNORECASE),
            "constraint": re.compile(r"(?:constraint|limitation|trade.?off|because|due to)", re.IGNORECASE),
            "alternative": re.compile(r"(?:alternative|instead|rather than|considered)", re.IGNORECASE),
            "pr_reference": re.compile(r"(?:PR #|pull request|#|issue)", re.IGNORECASE),
            "technical_term": re.compile(r"(?:TypeTag|TypeRepr|Mirror\.Of|sealed trait|macro|derivation)", re.IGNORECASE)
        }

    def analyze_repository_history(self, repo_path: str, depth_months: int = 24) -> Dict[str, Any]:
        """Analyze git history for forensic evidence.

        Args:
            repo_path: Path to the git repository
            depth_months: How many months of history to analyze

        Returns:
            Dictionary containing historical analysis results
        """
        try:
            repo = Repo(repo_path)
        except git.InvalidGitRepositoryError:
            return {}

        # Cache analysis to avoid repeated computation
        cache_key = f"{repo_path}_{depth_months}"
        if cache_key in self.repo_cache:
            return self.repo_cache[cache_key]

        # Get commits within time range
        since_date = datetime.now() - timedelta(days=depth_months * 30)
        commits = list(repo.iter_commits(since=since_date))

        analysis = {
            "total_commits": len(commits),
            "commit_patterns": self._analyze_commit_patterns(commits),
            "pr_history": self._analyze_pr_history(repo, commits),
            "technical_decisions": self._extract_technical_decisions(commits),
            "code_churn": self._analyze_code_churn(commits),
            "reviewer_patterns": self._analyze_reviewer_patterns(repo),
            "merge_patterns": self._analyze_merge_patterns(commits),
            "confidence_score": self._calculate_confidence_score(commits)
        }

        self.repo_cache[cache_key] = analysis
        return analysis

    def find_contextual_anchors(self, repo_path: str, current_topic: str,
                               maintainer_profile: Dict) -> List[Dict[str, Any]]:
        """Find historical PRs or commits that provide contextual anchors.

        Args:
            repo_path: Path to the repository
            current_topic: Current technical topic being addressed
            maintainer_profile: Maintainer's preferences and history

        Returns:
            List of contextual anchor references
        """
        history = self.analyze_repository_history(repo_path)

        anchors = []
        topic_keywords = self._extract_topic_keywords(current_topic)

        # Search through PR history for relevant topics
        for pr in history.get("pr_history", []):
            if self._topic_matches(pr, topic_keywords):
                anchor = {
                    "type": "pr_reference",
                    "reference": f"PR #{pr['number']}",
                    "title": pr["title"],
                    "relevance_score": self._calculate_relevance(pr, topic_keywords),
                    "technical_context": pr.get("technical_decisions", []),
                    "date": pr["date"]
                }
                anchors.append(anchor)

        # Search through technical decisions
        for decision in history.get("technical_decisions", []):
            if self._topic_matches_decision(decision, topic_keywords):
                anchor = {
                    "type": "technical_decision",
                    "reference": f"Decision from {decision['date']}",
                    "content": decision["content"],
                    "relevance_score": self._calculate_decision_relevance(decision, topic_keywords),
                    "commit_hash": decision["commit"]
                }
                anchors.append(anchor)

        # Sort by relevance and recency
        anchors.sort(key=lambda x: (x["relevance_score"], x.get("date", "")), reverse=True)

        return anchors[:5]  # Return top 5 anchors

    def generate_commit_style_profile(self, repo_path: str, maintainer: str) -> Dict[str, Any]:
        """Generate a profile of commit style patterns for a specific maintainer.

        Args:
            repo_path: Path to the repository
            maintainer: Maintainer's name or email

        Returns:
            Commit style profile
        """
        try:
            repo = Repo(repo_path)
        except git.InvalidGitRepositoryError:
            return {}

        # Find commits by this maintainer
        maintainer_commits = []
        for commit in repo.iter_commits():
            if maintainer.lower() in commit.author.name.lower() or \
               maintainer.lower() in commit.author.email.lower():
                maintainer_commits.append(commit)

        if not maintainer_commits:
            return {"error": "No commits found for maintainer"}

        return {
            "total_commits": len(maintainer_commits),
            "message_patterns": self._analyze_message_patterns(maintainer_commits),
            "commit_frequency": self._analyze_commit_frequency(maintainer_commits),
            "code_style": self._analyze_code_style(maintainer_commits),
            "collaboration_patterns": self._analyze_collaboration_patterns(maintainer_commits)
        }

    def _analyze_commit_patterns(self, commits: List[git.Commit]) -> Dict[str, Any]:
        """Analyze patterns in commit messages and structure."""
        messages = [commit.message for commit in commits]

        # Message length analysis
        message_lengths = [len(msg.split('\n')[0]) for msg in messages]
        avg_length = sum(message_lengths) / len(message_lengths) if message_lengths else 0

        # Conventional commit analysis
        conventional_pattern = re.compile(r'^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?:')
        conventional_count = sum(1 for msg in messages if conventional_pattern.match(msg))

        # Emoji usage
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]')
        emoji_count = sum(1 for msg in messages if emoji_pattern.search(msg))

        return {
            "avg_message_length": avg_length,
            "conventional_commits_ratio": conventional_count / len(messages) if messages else 0,
            "emoji_usage_ratio": emoji_count / len(messages) if messages else 0,
            "common_prefixes": self._extract_common_prefixes(messages)
        }

    def _analyze_pr_history(self, repo: Repo, commits: List[git.Commit]) -> List[Dict[str, Any]]:
        """Analyze pull request history from commits."""
        prs = []

        for commit in commits:
            # Look for PR references in commit messages
            pr_match = re.search(r'(?:PR #|pull request #|#)(\d+)', commit.message, re.IGNORECASE)
            if pr_match:
                pr_number = int(pr_match.group(1))

                # Try to get PR details (this would need GitHub API in real implementation)
                pr_info = {
                    "number": pr_number,
                    "title": self._extract_pr_title(commit.message),
                    "date": datetime.fromtimestamp(commit.committed_date).isoformat(),
                    "author": commit.author.name,
                    "technical_decisions": self._extract_technical_decisions_from_message(commit.message),
                    "review_comments": [],  # Would need API access
                    "merge_time": None  # Would need API access
                }
                prs.append(pr_info)

        return prs

    def _extract_technical_decisions(self, commits: List[git.Commit]) -> List[Dict[str, Any]]:
        """Extract technical decisions from commit messages."""
        decisions = []

        for commit in commits:
            message = commit.message
            if self.patterns["technical_decision"].search(message):
                decision = {
                    "content": message,
                    "date": datetime.fromtimestamp(commit.committed_date).isoformat(),
                    "commit": commit.hexsha[:8],
                    "author": commit.author.name,
                    "type": self._classify_decision_type(message),
                    "alternatives": self._extract_alternatives_from_message(message)
                }
                decisions.append(decision)

        return decisions

    def _analyze_code_churn(self, commits: List[git.Commit]) -> Dict[str, Any]:
        """Analyze code churn patterns."""
        churn_stats = defaultdict(int)

        for commit in commits:
            # Count additions and deletions
            if commit.stats.total['insertions'] > 0:
                churn_stats['insertions'] += commit.stats.total['insertions']
            if commit.stats.total['deletions'] > 0:
                churn_stats['deletions'] += commit.stats.total['deletions']
            if commit.stats.total['lines'] > 0:
                churn_stats['total_lines'] += commit.stats.total['lines']

        return dict(churn_stats)

    def _analyze_reviewer_patterns(self, repo: Repo) -> Dict[str, Any]:
        """Analyze reviewer patterns (simplified - would need API access for full analysis)."""
        # This is a placeholder - real implementation would use GitHub API
        return {
            "avg_review_time": None,  # Hours
            "common_reviewers": [],
            "review_comments_per_pr": 0,
            "approval_rate": 0.0
        }

    def _analyze_merge_patterns(self, commits: List[git.Commit]) -> Dict[str, Any]:
        """Analyze merge commit patterns."""
        merge_commits = [c for c in commits if len(c.parents) > 1]

        merge_times = []
        for merge in merge_commits:
            # Calculate time from first parent to merge
            if len(merge.parents) >= 2:
                time_diff = merge.committed_date - merge.parents[1].committed_date
                merge_times.append(time_diff / 3600)  # Hours

        return {
            "merge_commit_ratio": len(merge_commits) / len(commits) if commits else 0,
            "avg_merge_time_hours": sum(merge_times) / len(merge_times) if merge_times else 0,
            "merge_message_patterns": self._analyze_merge_messages(merge_commits)
        }

    def _calculate_confidence_score(self, commits: List[git.Commit]) -> float:
        """Calculate confidence score for historical analysis."""
        if not commits:
            return 0.0

        # Factors: volume, recency, consistency
        volume_score = min(1.0, len(commits) / 1000)  # Normalize to 1000 commits
        recency_score = self._calculate_recency_score(commits)
        consistency_score = self._calculate_consistency_score(commits)

        return (volume_score * 0.4 + recency_score * 0.3 + consistency_score * 0.3)

    def _calculate_recency_score(self, commits: List[git.Commit]) -> float:
        """Calculate how recent the commits are."""
        if not commits:
            return 0.0

        latest_commit = max(commits, key=lambda c: c.committed_date)
        days_since_latest = (datetime.now().timestamp() - latest_commit.committed_date) / 86400

        # Score decreases with time, 1.0 for < 30 days, 0.0 for > 365 days
        return max(0.0, 1.0 - (days_since_latest - 30) / 335)

    def _calculate_consistency_score(self, commits: List[git.Commit]) -> float:
        """Calculate consistency of commit patterns."""
        if len(commits) < 10:
            return 0.5  # Neutral for small datasets

        # Analyze commit frequency consistency
        dates = [datetime.fromtimestamp(c.committed_date).date() for c in commits]
        unique_dates = len(set(dates))

        # Consistency based on spread vs volume
        spread_ratio = unique_dates / len(commits)
        return min(1.0, spread_ratio * 2)  # Higher spread = more consistent

    def _extract_topic_keywords(self, topic: str) -> List[str]:
        """Extract keywords from a technical topic."""
        # Simple keyword extraction - could be enhanced with NLP
        words = re.findall(r'\b\w+\b', topic.lower())
        return [w for w in words if len(w) > 3]

    def _topic_matches(self, pr: Dict, keywords: List[str]) -> bool:
        """Check if PR matches topic keywords."""
        text = f"{pr.get('title', '')} {pr.get('description', '')}".lower()
        return any(keyword in text for keyword in keywords)

    def _topic_matches_decision(self, decision: Dict, keywords: List[str]) -> bool:
        """Check if decision matches topic keywords."""
        text = decision.get('content', '').lower()
        return any(keyword in text for keyword in keywords)

    def _calculate_relevance(self, pr: Dict, keywords: List[str]) -> float:
        """Calculate relevance score for a PR."""
        text = f"{pr.get('title', '')} {pr.get('description', '')}".lower()
        matches = sum(1 for keyword in keywords if keyword in text)
        return matches / len(keywords) if keywords else 0

    def _calculate_decision_relevance(self, decision: Dict, keywords: List[str]) -> float:
        """Calculate relevance score for a decision."""
        text = decision.get('content', '').lower()
        matches = sum(1 for keyword in keywords if keyword in text)
        return matches / len(keywords) if keywords else 0

    def _extract_pr_title(self, message: str) -> str:
        """Extract PR title from commit message."""
        lines = message.split('\n')
        return lines[0].strip()

    def _extract_technical_decisions_from_message(self, message: str) -> List[str]:
        """Extract technical decisions from commit message."""
        decisions = []
        lines = message.split('\n')

        for line in lines:
            if self.patterns["technical_decision"].search(line):
                decisions.append(line.strip())

        return decisions

    def _classify_decision_type(self, message: str) -> str:
        """Classify the type of technical decision."""
        if "performance" in message.lower():
            return "performance"
        elif "security" in message.lower():
            return "security"
        elif "api" in message.lower():
            return "api_design"
        elif "data" in message.lower():
            return "data_structure"
        else:
            return "implementation"

    def _extract_alternatives_from_message(self, message: str) -> List[str]:
        """Extract alternative approaches from message."""
        alternatives = []
        alt_match = self.patterns["alternative"].search(message)
        if alt_match:
            # Extract alternatives from context
            start = alt_match.start()
            end = message.find('\n', start)
            if end == -1:
                end = len(message)
            alt_text = message[start:end]
            alternatives = [alt.strip() for alt in alt_match.split(',') if alt.strip()]

        return alternatives

    def _extract_common_prefixes(self, messages: List[str]) -> List[Tuple[str, int]]:
        """Extract common commit message prefixes."""
        prefixes = Counter()
        for msg in messages:
            first_line = msg.split('\n')[0]
            words = first_line.split()
            if words:
                prefix = words[0].lower()
                prefixes[prefix] += 1

        return prefixes.most_common(10)

    def _analyze_message_patterns(self, commits: List[git.Commit]) -> Dict[str, Any]:
        """Analyze commit message patterns for a maintainer."""
        messages = [c.message for c in commits]
        return self._analyze_commit_patterns(commits)  # Reuse existing logic

    def _analyze_commit_frequency(self, commits: List[git.Commit]) -> Dict[str, Any]:
        """Analyze commit frequency patterns."""
        dates = [datetime.fromtimestamp(c.committed_date).date() for c in commits]
        date_counts = Counter(dates)

        return {
            "avg_commits_per_day": len(commits) / len(date_counts) if date_counts else 0,
            "most_active_day": date_counts.most_common(1)[0][0].isoformat() if date_counts else None,
            "consistency_score": self._calculate_consistency_score(commits)
        }

    def _analyze_code_style(self, commits: List[git.Commit]) -> Dict[str, Any]:
        """Analyze code style patterns (simplified)."""
        # This would need actual code analysis
        return {
            "indentation_style": "unknown",
            "naming_conventions": "unknown",
            "comment_density": 0.0
        }

    def _analyze_collaboration_patterns(self, commits: List[git.Commit]) -> Dict[str, Any]:
        """Analyze collaboration patterns."""
        authors = Counter(c.author.name for c in commits)
        co_authors = sum(1 for c in commits if len(c.message.split('\n')) > 1 and 'Co-authored-by:' in c.message)

        return {
            "unique_contributors": len(authors),
            "pair_programming_ratio": co_authors / len(commits) if commits else 0,
            "collaboration_score": min(1.0, len(authors) / 10)  # Normalize
        }

    def _analyze_merge_messages(self, merge_commits: List[git.Commit]) -> Dict[str, Any]:
        """Analyze merge commit message patterns."""
        messages = [c.message for c in merge_commits]
        return self._analyze_commit_patterns(merge_commits)