#!/usr/bin/env python3
"""
Repository Validation Data Collection System

This script systematically collects 50+ real-world repository samples across all supported
languages and repository types to validate the repository scanner's effectiveness.

Supported Languages: Python, Java, Rust, JavaScript/TypeScript, Go, C++
Repository Types: Libraries, Web Apps, Enterprise Apps, CLI Tools, Data Science, etc.
"""

import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import requests
import time


@dataclass
class RepositoryMetadata:
    """Metadata for a validation repository."""
    name: str
    url: str
    language: str
    repo_type: str
    complexity: str  # 'simple', 'medium', 'complex', 'enterprise'
    size_category: str  # 'small', 'medium', 'large', 'xlarge'
    stars: Optional[int] = None
    description: Optional[str] = None
    collected_at: Optional[str] = None
    file_count: Optional[int] = None
    total_size_bytes: Optional[int] = None
    primary_language: Optional[str] = None
    has_tests: bool = False
    has_docs: bool = False
    has_ci: bool = False
    validation_status: str = 'pending'  # 'pending', 'collected', 'validated', 'failed'


class ValidationDataCollector:
    """Collects and manages validation repository data."""

    def __init__(self, base_dir: str = "validation_data/repositories"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.base_dir / "repositories_metadata.json"
        self.target_count = 50

        # Repository sources by language and type
        self.repository_sources = {
            'python': {
                'libraries': [
                    'https://github.com/psf/requests',
                    'https://github.com/pallets/flask',
                    'https://github.com/pandas-dev/pandas',
                    'https://github.com/numpy/numpy',
                    'https://github.com/scikit-learn/scikit-learn',
                    'https://github.com/django/django',
                    'https://github.com/fastapi/fastapi',
                    'https://github.com/tiangolo/sqlmodel',
                ],
                'web_apps': [
                    'https://github.com/miguelgrinberg/flasky',
                    'https://github.com/realpython/discover-flask',
                    'https://github.com/pallets/flask-website',
                ],
                'data_science': [
                    'https://github.com/jupyter/notebook',
                    'https://github.com/scipy/scipy',
                    'https://github.com/matplotlib/matplotlib',
                ],
                'cli_tools': [
                    'https://github.com/tqdm/tqdm',
                    'https://github.com/pallets/click',
                    'https://github.com/Textualize/rich',
                ]
            },
            'java': {
                'libraries': [
                    'https://github.com/google/guava',
                    'https://github.com/apache/commons-lang',
                    'https://github.com/spring-projects/spring-framework',
                    'https://github.com/apache/log4j',
                ],
                'web_apps': [
                    'https://github.com/spring-projects/spring-petclinic',
                    'https://github.com/spring-projects/spring-boot',
                ],
                'enterprise': [
                    'https://github.com/wildfly/wildfly',
                    'https://github.com/apache/camel',
                ]
            },
            'rust': {
                'libraries': [
                    'https://github.com/rust-lang/regex',
                    'https://github.com/serde-rs/serde',
                    'https://github.com/tokio-rs/tokio',
                    'https://github.com/hyperium/hyper',
                ],
                'cli_tools': [
                    'https://github.com/sharkdp/bat',
                    'https://github.com/BurntSushi/ripgrep',
                    'https://github.com/sharkdp/fd',
                ],
                'web_services': [
                    'https://github.com/actix/actix-web',
                    'https://github.com/rocket/rocket',
                ]
            },
            'javascript': {
                'libraries': [
                    'https://github.com/lodash/lodash',
                    'https://github.com/moment/moment',
                    'https://github.com/expressjs/express',
                    'https://github.com/facebook/react',
                ],
                'web_apps': [
                    'https://github.com/facebook/create-react-app',
                    'https://github.com/vercel/next.js',
                    'https://github.com/vuejs/vue',
                ],
                'tools': [
                    'https://github.com/webpack/webpack',
                    'https://github.com/babel/babel',
                ]
            },
            'go': {
                'libraries': [
                    'https://github.com/golang/go',
                    'https://github.com/gorilla/mux',
                    'https://github.com/gin-gonic/gin',
                    'https://github.com/uber-go/zap',
                ],
                'cli_tools': [
                    'https://github.com/spf13/cobra',
                    'https://github.com/urfave/cli',
                ],
                'web_services': [
                    'https://github.com/kubernetes/kubernetes',
                    'https://github.com/prometheus/prometheus',
                ]
            },
            'cpp': {
                'libraries': [
                    'https://github.com/google/googletest',
                    'https://github.com/fmtlib/fmt',
                    'https://github.com/gabime/spdlog',
                    'https://github.com/nlohmann/json',
                ],
                'tools': [
                    'https://github.com/opencv/opencv',
                    'https://github.com/protocolbuffers/protobuf',
                ],
                'applications': [
                    'https://github.com/electron/electron',
                    'https://github.com/nodejs/node',
                ]
            }
        }

    def load_metadata(self) -> Dict[str, RepositoryMetadata]:
        """Load existing repository metadata."""
        if not self.metadata_file.exists():
            return {}

        try:
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
                return {k: RepositoryMetadata(**v) for k, v in data.items()}
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return {}

    def save_metadata(self, metadata: Dict[str, RepositoryMetadata]):
        """Save repository metadata."""
        try:
            data = {k: asdict(v) for k, v in metadata.items()}
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving metadata: {e}")

    def get_repository_info(self, url: str) -> Tuple[str, str]:
        """Extract repository name and determine type from URL."""
        # Extract repo name from URL
        parts = url.rstrip('/').split('/')
        repo_name = f"{parts[-2]}_{parts[-1]}"

        # Determine language from URL patterns or manual mapping
        language = 'unknown'
        if 'github.com' in url:
            # Try to infer language from common patterns
            if any(lib in url.lower() for lib in ['psf/', 'pallets/', 'django/', 'numpy/', 'pandas/', 'scipy/', 'matplotlib/']):
                language = 'python'
            elif any(lib in url.lower() for lib in ['google/', 'apache/', 'spring-projects/']):
                language = 'java'
            elif any(lib in url.lower() for lib in ['rust-lang/', 'serde-rs/', 'tokio-rs/', 'hyperium/', 'actix/', 'rocket/']):
                language = 'rust'
            elif any(lib in url.lower() for lib in ['lodash/', 'moment/', 'expressjs/', 'facebook/', 'vuejs/', 'webpack/', 'babel/']):
                language = 'javascript'
            elif any(lib in url.lower() for lib in ['golang/', 'gorilla/', 'gin-gonic/', 'uber-go/', 'spf13/', 'urfave/']):
                language = 'go'
            elif any(lib in url.lower() for lib in ['google/', 'fmtlib/', 'gabime/', 'nlohmann/', 'opencv/', 'protocolbuffers/']):
                language = 'cpp'

        return repo_name, language

    def clone_repository(self, url: str, target_dir: Path) -> bool:
        """Clone a repository to the target directory."""
        try:
            print(f"Cloning {url} to {target_dir}")
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', url, str(target_dir)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            print(f"Failed to clone {url}: {e}")
            return False

    def analyze_repository(self, repo_dir: Path) -> RepositoryMetadata:
        """Analyze a cloned repository and extract metadata."""
        metadata = RepositoryMetadata(
            name=repo_dir.name,
            url="",  # Will be set later
            language="unknown",
            repo_type="unknown",
            complexity="medium",
            size_category="medium"
        )

        try:
            # Count files and calculate size
            total_files = 0
            total_size = 0
            has_tests = False
            has_docs = False
            has_ci = False

            for root, dirs, files in os.walk(repo_dir):
                # Skip .git directory
                if '.git' in dirs:
                    dirs.remove('.git')

                for file in files:
                    file_path = Path(root) / file
                    total_files += 1
                    try:
                        total_size += file_path.stat().st_size
                    except OSError:
                        pass

                    # Check for test files
                    if any(test_dir in str(file_path) for test_dir in ['test', 'tests', 'spec', '__tests__']):
                        has_tests = True

                    # Check for documentation
                    if file.lower() in ['readme.md', 'readme.txt', 'readme.rst', 'docs', 'documentation']:
                        has_docs = True

                    # Check for CI
                    if file.lower() in ['.github', '.travis.yml', '.gitlab-ci.yml', 'azure-pipelines.yml']:
                        has_ci = True

            metadata.file_count = total_files
            metadata.total_size_bytes = total_size
            metadata.has_tests = has_tests
            metadata.has_docs = has_docs
            metadata.has_ci = has_ci
            metadata.collected_at = datetime.now().isoformat()

            # Determine complexity based on file count and size
            if total_files < 50:
                metadata.complexity = 'simple'
            elif total_files < 500:
                metadata.complexity = 'medium'
            elif total_files < 2000:
                metadata.complexity = 'complex'
            else:
                metadata.complexity = 'enterprise'

            # Determine size category
            size_mb = total_size / (1024 * 1024)
            if size_mb < 10:
                metadata.size_category = 'small'
            elif size_mb < 100:
                metadata.size_category = 'medium'
            elif size_mb < 500:
                metadata.size_category = 'large'
            else:
                metadata.size_category = 'xlarge'

        except Exception as e:
            print(f"Error analyzing repository {repo_dir}: {e}")

        return metadata

    def collect_repositories(self) -> Dict[str, RepositoryMetadata]:
        """Collect repositories from all sources."""
        metadata = self.load_metadata()
        collected_count = len([m for m in metadata.values() if m.validation_status == 'collected'])

        print(f"Starting collection. Currently have {collected_count}/{self.target_count} repositories.")

        # Collect repositories by language and type
        for language, types in self.repository_sources.items():
            for repo_type, urls in types.items():
                for url in urls:
                    if collected_count >= self.target_count:
                        break

                    repo_name, detected_language = self.get_repository_info(url)

                    # Skip if already collected
                    if repo_name in metadata and metadata[repo_name].validation_status == 'collected':
                        continue

                    print(f"Collecting {repo_name} ({language}/{repo_type})")

                    # Create repository directory
                    repo_dir = self.base_dir / repo_name
                    if repo_dir.exists():
                        shutil.rmtree(repo_dir)

                    # Clone repository
                    if self.clone_repository(url, repo_dir):
                        # Analyze repository
                        repo_metadata = self.analyze_repository(repo_dir)
                        repo_metadata.name = repo_name
                        repo_metadata.url = url
                        repo_metadata.language = detected_language or language
                        repo_metadata.repo_type = repo_type
                        repo_metadata.validation_status = 'collected'

                        metadata[repo_name] = repo_metadata
                        collected_count += 1

                        print(f"Successfully collected {repo_name} ({repo_metadata.file_count} files, {repo_metadata.total_size_bytes} bytes)")
                    else:
                        # Mark as failed
                        if repo_name not in metadata:
                            metadata[repo_name] = RepositoryMetadata(
                                name=repo_name,
                                url=url,
                                language=detected_language or language,
                                repo_type=repo_type,
                                complexity='unknown',
                                size_category='unknown',
                                validation_status='failed'
                            )

                    # Save progress
                    self.save_metadata(metadata)

                    # Small delay to be respectful to GitHub
                    time.sleep(1)

        print(f"Collection complete. Total repositories: {len(metadata)}")
        successful = len([m for m in metadata.values() if m.validation_status == 'collected'])
        print(f"Successfully collected: {successful}/{self.target_count}")

        return metadata

    def validate_collection(self) -> Dict[str, any]:
        """Validate the collected repositories."""
        metadata = self.load_metadata()
        validation_results = {
            'total_repositories': len(metadata),
            'collected_count': 0,
            'failed_count': 0,
            'language_distribution': {},
            'type_distribution': {},
            'complexity_distribution': {},
            'size_distribution': {},
            'coverage_gaps': []
        }

        for repo_meta in metadata.values():
            if repo_meta.validation_status == 'collected':
                validation_results['collected_count'] += 1

                # Update distributions
                validation_results['language_distribution'][repo_meta.language] = \
                    validation_results['language_distribution'].get(repo_meta.language, 0) + 1
                validation_results['type_distribution'][repo_meta.repo_type] = \
                    validation_results['type_distribution'].get(repo_meta.repo_type, 0) + 1
                validation_results['complexity_distribution'][repo_meta.complexity] = \
                    validation_results['complexity_distribution'].get(repo_meta.complexity, 0) + 1
                validation_results['size_distribution'][repo_meta.size_category] = \
                    validation_results['size_distribution'].get(repo_meta.size_category, 0) + 1
            elif repo_meta.validation_status == 'failed':
                validation_results['failed_count'] += 1

        # Check for coverage gaps
        required_languages = {'python', 'java', 'rust', 'javascript', 'go', 'cpp'}
        current_languages = set(validation_results['language_distribution'].keys())
        missing_languages = required_languages - current_languages
        if missing_languages:
            validation_results['coverage_gaps'].append(f"Missing languages: {missing_languages}")

        # Check minimum counts per language
        min_per_language = 5
        for lang in required_languages:
            count = validation_results['language_distribution'].get(lang, 0)
            if count < min_per_language:
                validation_results['coverage_gaps'].append(f"Language {lang}: {count}/{min_per_language} repositories")

        return validation_results


def main():
    """Main collection function."""
    collector = ValidationDataCollector()

    print("Starting repository validation data collection...")
    print(f"Target: {collector.target_count} repositories across all supported languages")

    # Collect repositories
    metadata = collector.collect_repositories()

    # Validate collection
    validation_results = collector.validate_collection()

    print("\n=== Collection Summary ===")
    print(f"Total repositories: {validation_results['total_repositories']}")
    print(f"Successfully collected: {validation_results['collected_count']}")
    print(f"Failed: {validation_results['failed_count']}")

    print("\n=== Language Distribution ===")
    for lang, count in validation_results['language_distribution'].items():
        print(f"  {lang}: {count}")

    print("\n=== Repository Types ===")
    for repo_type, count in validation_results['type_distribution'].items():
        print(f"  {repo_type}: {count}")

    print("\n=== Complexity Distribution ===")
    for complexity, count in validation_results['complexity_distribution'].items():
        print(f"  {complexity}: {count}")

    if validation_results['coverage_gaps']:
        print("\n=== Coverage Gaps ===")
        for gap in validation_results['coverage_gaps']:
            print(f"  ⚠️  {gap}")

    # Save validation results
    results_file = collector.base_dir / "collection_validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(validation_results, f, indent=2)

    success = validation_results['collected_count'] >= collector.target_count and not validation_results['coverage_gaps']
    print(f"\nCollection {'SUCCESSFUL' if success else 'INCOMPLETE'}")
    return success


if __name__ == "__main__":
    main()