"""Unit tests for SQL Injection Validator."""

import pytest
from src.core.security.sql_injection_validator import SQLInjectionValidator


@pytest.fixture
def validator():
    """Create SQL injection validator instance."""
    return SQLInjectionValidator()


class TestSQLInjectionPatterns:
    """Test SQL injection pattern detection."""
    
    def test_unsafe_string_concatenation(self, validator):
        """Test detection of string concatenation in SQL."""
        code = 'query = "SELECT * FROM users WHERE id = " + user_id'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
        assert "concatenation" in reason.lower()
    
    def test_unsafe_fstring(self, validator):
        """Test detection of f-strings in SQL."""
        code = 'query = f"SELECT * FROM users WHERE id = {user_id}"'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
        assert "f-string" in reason.lower()
    
    def test_unsafe_format_method(self, validator):
        """Test detection of .format() in SQL."""
        code = 'query = "SELECT * FROM users WHERE id = {}".format(user_id)'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
    
    def test_unsafe_percent_formatting(self, validator):
        """Test detection of % formatting in SQL."""
        code = 'query = "SELECT * FROM users WHERE id = %s" % user_id'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
    
    def test_safe_parameterized_query(self, validator):
        """Test safe parameterized query is not flagged."""
        code = 'cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert not is_vuln
        assert confidence < 0.3
    
    def test_safe_orm_filter(self, validator):
        """Test ORM .filter() is not flagged."""
        code = 'User.objects.filter(id=user_id)'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "models.py", 10, "from django.db import models", []
        )
        assert not is_vuln
    
    def test_safe_sqlalchemy_query(self, validator):
        """Test SQLAlchemy parameterized query is safe."""
        code = 'session.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "from sqlalchemy import text", []
        )
        assert not is_vuln


class TestContextAnalysis:
    """Test context-aware analysis."""
    
    def test_test_file_reduces_confidence(self, validator):
        """Test that test files reduce confidence."""
        code = 'query = "SELECT * FROM users WHERE id = " + user_id'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "test_models.py", 10, "", []
        )
        # Should still detect but with lower confidence
        assert confidence < 0.5
        assert "test file" in reason.lower()
    
    def test_static_query_not_vulnerable(self, validator):
        """Test static queries are not flagged."""
        code = 'query = "SELECT * FROM users WHERE id = 123"'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert not is_vuln
        # Static query with no unsafe patterns is correctly not detected
        assert "no unsafe" in reason.lower() or "static" in reason.lower()
    
    def test_sanitization_reduces_confidence(self, validator):
        """Test input sanitization reduces confidence."""
        code = 'query = f"SELECT * FROM users WHERE id = {user_id}"'
        context = [
            "user_id = request.GET['id']",
            "user_id = int(user_id)",  # Sanitization
            code
        ]
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", context
        )
        # Sanitization should reduce confidence
        assert confidence < 0.5 or not is_vuln


class TestFrameworkSpecific:
    """Test framework-specific patterns."""
    
    def test_django_orm_safe(self, validator):
        """Test Django ORM methods are safe."""
        file_content = "from django.db import models\n"
        safe_patterns = [
            'User.objects.filter(id=user_id)',
            'User.objects.get(pk=user_id)',
            'User.objects.all()',
            'User.objects.create(name=name)',
        ]
        
        for code in safe_patterns:
            is_vuln, _, _ = validator.validate_sql_operation(
                code, "models.py", 10, file_content, []
            )
            assert not is_vuln, f"Django ORM pattern should be safe: {code}"
    
    def test_sqlalchemy_orm_safe(self, validator):
        """Test SQLAlchemy ORM methods are safe."""
        file_content = "from sqlalchemy import select\n"
        safe_patterns = [
            'session.query(User).filter(User.id == user_id)',
            'session.query(User).filter_by(id=user_id)',
            'select(User).where(User.id == user_id)',
        ]
        
        for code in safe_patterns:
            is_vuln, _, _ = validator.validate_sql_operation(
                code, "models.py", 10, file_content, []
            )
            assert not is_vuln, f"SQLAlchemy pattern should be safe: {code}"


class TestEdgeCases:
    """Test edge cases and corner scenarios."""
    
    def test_multiline_query(self, validator):
        """Test multiline SQL queries."""
        code = '''query = "SELECT * FROM users WHERE " + \\
                         "id = " + user_id'''
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
    
    def test_insert_statement(self, validator):
        """Test INSERT statement detection."""
        code = 'query = f"INSERT INTO users (name) VALUES ({name})"'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
    
    def test_update_statement(self, validator):
        """Test UPDATE statement detection."""
        code = 'query = "UPDATE users SET name = " + name'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
    
    def test_delete_statement(self, validator):
        """Test DELETE statement detection."""
        code = 'query = f"DELETE FROM users WHERE id = {user_id}"'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestFalsePositiveReduction:
    """Test that English words containing SQL keywords are NOT flagged."""

    def test_fstring_with_updated_english_word(self, validator):
        """f-string with 'Updated' (contains UPDATE) should NOT be flagged."""
        code = 'print(f"Updated {count} records")'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert not is_vuln

    def test_fstring_with_selected_english_word(self, validator):
        """f-string with 'Selected' (contains SELECT) should NOT be flagged."""
        code = 'print(f"Selected {item} from list")'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert not is_vuln

    def test_fstring_with_deleted_english_word(self, validator):
        """f-string with 'Deleted' (contains DELETE) should NOT be flagged."""
        code = 'print(f"Deleted {n} entries")'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert not is_vuln

    def test_fstring_with_inserted_english_word(self, validator):
        """f-string with 'Inserted' should NOT be flagged."""
        code = 'print(f"Inserted {n} rows into the log")'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert not is_vuln

    def test_real_sql_select_fstring_still_detected(self, validator):
        """Real SQL SELECT in f-string SHOULD be flagged."""
        code = 'query = f"SELECT * FROM users WHERE id = {user_id}"'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7

    def test_real_sql_update_fstring_still_detected(self, validator):
        """Real SQL UPDATE in f-string SHOULD be flagged."""
        code = "query = f\"UPDATE users SET name = '{name}'\""  # noqa
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7

    def test_real_sql_delete_fstring_still_detected(self, validator):
        """Real SQL DELETE FROM in f-string SHOULD be flagged."""
        code = 'query = f"DELETE FROM users WHERE id = {user_id}"'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7

    def test_real_sql_insert_fstring_still_detected(self, validator):
        """Real SQL INSERT INTO in f-string SHOULD be flagged."""
        code = 'query = f"INSERT INTO users VALUES ({name}, {email})"'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7

    def test_parameterized_query_still_safe(self, validator):
        """Parameterized queries should NOT be flagged."""
        code = 'cursor.execute("SELECT * FROM users WHERE id = ?", (uid,))'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert not is_vuln

    def test_format_with_real_sql_still_detected(self, validator):
        """SQL with .format() SHOULD be flagged."""
        code = 'query = "SELECT * FROM users WHERE id = {}".format(uid)'
        is_vuln, reason, confidence = validator.validate_sql_operation(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
