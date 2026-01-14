"""
ML-based Pattern Detection Module

Uses machine learning to detect unknown vulnerability patterns in code
that may not be covered by traditional rule-based detection.
"""

from typing import Dict, Any, List, Optional
import os
import pickle
from pathlib import Path
import hashlib

from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
import numpy as np

from ..adapters.language_adapter_manager import LanguageAdapterManager


class MLPatternDetector:
    """
    Machine learning-based detector for unknown vulnerability patterns.

    Uses anomaly detection algorithms to identify code patterns that deviate
    from normal, potentially indicating security vulnerabilities.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the ML pattern detector.

        Args:
            model_path: Path to pre-trained model file
        """
        self.model_path = model_path or os.path.join(os.path.dirname(__file__), "ml_model.pkl")
        self.isolation_forest = None
        self.vectorizer = None
        self.scaler = None
        self.language_adapter = LanguageAdapterManager()

        # Load or train model
        self._load_or_train_model()

    def _load_or_train_model(self):
        """Load existing model or train a new one."""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.isolation_forest = model_data['isolation_forest']
                    self.vectorizer = model_data['vectorizer']
                    self.scaler = model_data['scaler']
                print("Loaded pre-trained ML model for pattern detection")
            except Exception as e:
                print(f"Failed to load model: {e}. Training new model.")
                self._train_model()
        else:
            self._train_model()

    def _train_model(self):
        """Train the ML model on sample code data."""
        # Sample training data - in production, this would be a large dataset
        # of known safe and vulnerable code snippets
        training_samples = self._get_training_samples()

        if not training_samples:
            # Fallback: create a basic model
            self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
            self.vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 3))
            self.scaler = StandardScaler()
            return

        # Extract features
        features = []
        for sample in training_samples:
            feature_vector = self._extract_features(sample['code'], sample['language'])
            if feature_vector is not None:
                features.append(feature_vector)

        if not features:
            return

        # Convert to numpy array
        X = np.array(features)

        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Train isolation forest for anomaly detection
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.isolation_forest.fit(X_scaled)

        # Save model
        model_data = {
            'isolation_forest': self.isolation_forest,
            'vectorizer': self.vectorizer,
            'scaler': self.scaler
        }

        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            print("Trained and saved new ML model")
        except Exception as e:
            print(f"Failed to save model: {e}")

    def _get_training_samples(self) -> List[Dict[str, Any]]:
        """Get training samples for the ML model."""
        # This is a simplified example. In production, you'd have a large dataset
        # of labeled code samples (safe vs vulnerable)
        samples = [
            {
                'code': 'def login(username, password):\n    if username == "admin" and password == "secret":\n        return True',
                'language': 'python',
                'is_vulnerable': True
            },
            {
                'code': 'import os\napi_key = os.getenv("API_KEY")',
                'language': 'python',
                'is_vulnerable': False
            },
            {
                'code': 'function authenticate(user, pass) {\n    return user === "admin" && pass === "123456";\n}',
                'language': 'javascript',
                'is_vulnerable': True
            },
            {
                'code': 'const apiKey = process.env.API_KEY;',
                'language': 'javascript',
                'is_vulnerable': False
            }
        ]
        return samples

    def _extract_features(self, code: str, language: str) -> Optional[List[float]]:
        """
        Extract numerical features from code for ML analysis.

        Args:
            code: Source code snippet
            language: Programming language

        Returns:
            List of numerical features
        """
        try:
            features = []

            # Basic text features
            features.append(len(code))  # Code length
            features.append(len(code.split()))  # Word count
            features.append(len(code.split('\n')))  # Line count

            # Get AST features if possible
            ast_features = self._extract_ast_features(code, language)
            features.extend(ast_features)

            # Code complexity features
            features.append(self._calculate_complexity(code, language))

            # Security-relevant token counts
            security_tokens = ['password', 'secret', 'key', 'token', 'auth', 'encrypt']
            token_count = sum(code.lower().count(token) for token in security_tokens)
            features.append(token_count)

            return features

        except Exception as e:
            print(f"Error extracting features: {e}")
            return None

    def _extract_ast_features(self, code: str, language: str) -> List[float]:
        """Extract AST-based features."""
        try:
            adapter = self.language_adapter.get_adapter_for_language(language)
            if not adapter:
                return [0.0] * 10  # Default features

            ast_result = adapter.extract_ast_from_code(code)
            ast_data = ast_result.get('ast', {})

            features = [
                ast_data.get('node_count', 0),
                ast_data.get('function_count', 0),
                ast_data.get('class_count', 0),
                ast_data.get('import_count', 0),
                ast_data.get('variable_count', 0),
                ast_data.get('string_literal_count', 0),
                ast_data.get('numeric_literal_count', 0),
                len(ast_data.get('unsafe_patterns', [])),
                ast_data.get('complexity_score', 0),
                ast_data.get('max_depth', 0)
            ]

            return features

        except Exception:
            return [0.0] * 10

    def _calculate_complexity(self, code: str, language: str) -> float:
        """Calculate code complexity score."""
        # Simple complexity based on keywords and control structures
        complexity_keywords = {
            'python': ['if', 'for', 'while', 'def', 'class', 'try', 'except'],
            'javascript': ['if', 'for', 'while', 'function', 'class', 'try', 'catch'],
            'java': ['if', 'for', 'while', 'method', 'class', 'try', 'catch']
        }

        keywords = complexity_keywords.get(language, [])
        complexity = sum(code.count(keyword) for keyword in keywords)

        # Add complexity for nesting (indentation)
        if language == 'python':
            indentation_levels = [len(line) - len(line.lstrip()) for line in code.split('\n') if line.strip()]
            complexity += sum(level // 4 for level in indentation_levels)  # 4 spaces per level

        return float(complexity)

    def detect_patterns(self, file_path: str) -> Dict[str, Any]:
        """
        Detect potential vulnerability patterns in a file using ML.

        Args:
            file_path: Path to the file to analyze

        Returns:
            Dict containing detection results
        """
        if not self.isolation_forest:
            return {
                "ml_analysis": "Model not available",
                "anomalies_detected": [],
                "confidence": 0.0
            }

        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()

            # Determine language
            language = self._detect_language(file_path)

            # Extract features
            features = self._extract_features(code, language)
            if features is None:
                return {
                    "ml_analysis": "Feature extraction failed",
                    "anomalies_detected": [],
                    "confidence": 0.0
                }

            # Scale features
            X = np.array([features])
            X_scaled = self.scaler.transform(X)

            # Predict anomaly score
            anomaly_score = self.isolation_forest.decision_function(X_scaled)[0]
            is_anomaly = self.isolation_forest.predict(X_scaled)[0] == -1

            # Convert anomaly score to confidence (higher score = more normal)
            confidence = 1.0 / (1.0 + np.exp(-anomaly_score))  # Sigmoid

            result = {
                "ml_analysis": "completed",
                "anomalies_detected": [],
                "confidence": float(confidence),
                "is_anomaly": bool(is_anomaly),
                "anomaly_score": float(anomaly_score),
                "features_extracted": len(features),
                "language": language
            }

            if is_anomaly:
                result["anomalies_detected"].append({
                    "type": "ml_detected_anomaly",
                    "description": "Code pattern detected as anomalous by ML model",
                    "severity": "medium" if confidence < 0.7 else "low",
                    "confidence": confidence,
                    "file": str(file_path),
                    "recommendation": "Manual security review recommended for this code pattern"
                })

            return result

        except Exception as e:
            return {
                "ml_analysis": f"Error: {str(e)}",
                "anomalies_detected": [],
                "confidence": 0.0
            }

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust'
        }
        return language_map.get(ext, 'unknown')

    def analyze_repository(self, repo_path: str) -> Dict[str, Any]:
        """
        Analyze entire repository for ML-detected patterns.

        Args:
            repo_path: Path to repository

        Returns:
            Dict containing repository-wide analysis
        """
        repo = Path(repo_path)
        analysis_results = {
            "total_files_analyzed": 0,
            "anomalies_found": 0,
            "high_confidence_anomalies": 0,
            "files_with_anomalies": [],
            "ml_summary": {}
        }

        # Analyze code files
        code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs']

        for file_path in repo.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in code_extensions:
                result = self.detect_patterns(str(file_path))
                analysis_results["total_files_analyzed"] += 1

                if result.get("anomalies_detected"):
                    analysis_results["anomalies_found"] += len(result["anomalies_detected"])
                    analysis_results["files_with_anomalies"].append(str(file_path))

                    for anomaly in result["anomalies_detected"]:
                        if anomaly.get("confidence", 0) > 0.8:
                            analysis_results["high_confidence_anomalies"] += 1

        analysis_results["ml_summary"] = {
            "anomaly_detection_enabled": True,
            "model_type": "IsolationForest",
            "analysis_coverage": f"{analysis_results['total_files_analyzed']} files analyzed",
            "risk_assessment": self._assess_risk(analysis_results)
        }

        return analysis_results

    def _assess_risk(self, results: Dict[str, Any]) -> str:
        """Assess overall risk based on analysis results."""
        anomalies = results.get("anomalies_found", 0)
        high_conf = results.get("high_confidence_anomalies", 0)
        total_files = results.get("total_files_analyzed", 1)

        anomaly_rate = anomalies / total_files

        if high_conf > 0 or anomaly_rate > 0.1:
            return "HIGH - Multiple high-confidence anomalies detected"
        elif anomalies > 0:
            return "MEDIUM - Anomalies detected, manual review recommended"
        else:
            return "LOW - No significant anomalies detected"