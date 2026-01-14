import tempfile
from pathlib import Path

from src.core.pipeline.repository_discovery import get_canonical_file_list


def test_excludes_skip_generated_dirs_and_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    # create various dirs and files, some should be excluded
    (repo / "src").mkdir()
    (repo / "src" / "main.py").write_text("print('x')")

    (repo / "tmp_scan_output").mkdir()
    (repo / "tmp_scan_output" / "scan_report.json").write_text("{}")

    (repo / ".scanner_cache").mkdir()
    (repo / ".scanner_cache" / "cache.dat").write_text("data")

    (repo / "dist").mkdir()
    (repo / "dist" / "bundle.min.js").write_text("console.log(1)")

    (repo / "lib.so").write_text("")

    files = get_canonical_file_list(str(repo))
    # Paths that should NOT be present
    assert not any('tmp_scan_output' in p for p in files)
    assert not any('.scanner_cache' in p for p in files)
    assert not any('bundle.min.js' in p for p in files)
    assert not any('lib.so' in p for p in files)
    # Files that should be present
    assert any('src/main.py' in p for p in files)


def test_excludes_comprehensive_directory_exclusions(tmp_path):
    """Test that all major categories of generated/cached/output directories are excluded."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Create source file that should be included
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("print('hello')")

    # Python exclusions
    (repo / "__pycache__").mkdir()
    (repo / "__pycache__" / "module.pyc").write_text("bytecode")
    (repo / ".pytest_cache").mkdir()
    (repo / ".pytest_cache" / "cache.db").write_text("cache")
    (repo / "venv").mkdir()
    (repo / "venv" / "bin").mkdir(parents=True)
    (repo / "venv" / "bin" / "python").write_text("#!/bin/bash")

    # JavaScript/Node exclusions
    (repo / "node_modules").mkdir()
    (repo / "node_modules" / "package.json").write_text("{}")
    (repo / ".npm").mkdir()
    (repo / ".npm" / "cache.db").write_text("npm cache")

    # Build tool exclusions
    (repo / "build").mkdir()
    (repo / "build" / "output.jar").write_text("jar content")
    (repo / "dist").mkdir()
    (repo / "dist" / "app.exe").write_text("exe content")
    (repo / "target").mkdir()
    (repo / "target" / "classes").mkdir()
    (repo / "target" / "classes" / "App.class").write_text("class file")

    # IDE exclusions
    (repo / ".idea").mkdir()
    (repo / ".idea" / "workspace.xml").write_text("<xml>")
    (repo / ".vscode").mkdir()
    (repo / ".vscode" / "settings.json").write_text("{}")

    # Cache exclusions
    (repo / ".cache").mkdir()
    (repo / ".cache" / "data").write_text("cached data")
    (repo / "coverage").mkdir()
    (repo / "coverage" / "index.html").write_text("<html>")

    # Output exclusions
    (repo / "outputs").mkdir()
    (repo / "outputs" / "result.json").write_text("{}")
    (repo / "reports").mkdir()
    (repo / "reports" / "report.pdf").write_text("pdf content")

    # CI/CD exclusions
    (repo / ".github").mkdir()
    (repo / ".github" / "workflows").mkdir()
    (repo / ".github" / "workflows" / ".cache").mkdir()
    (repo / ".github" / "workflows" / ".cache" / "data").write_text("ci cache")

    files = get_canonical_file_list(str(repo))

    # Assert source files are included
    assert any('src/app.py' in p for p in files), "Source files should be included"

    # Assert all excluded directories are properly excluded
    excluded_patterns = [
        '__pycache__', '.pytest_cache', 'venv',
        'node_modules', '.npm',
        'build', 'dist', 'target',
        '.idea', '.vscode',
        '.cache', 'coverage',
        'outputs', 'reports',
        '.github/workflows/.cache'
    ]

    for pattern in excluded_patterns:
        assert not any(pattern in p for p in files), f"Pattern '{pattern}' should be excluded but found in: {[p for p in files if pattern in p]}"


def test_excludes_file_extensions(tmp_path):
    """Test that generated and temporary file extensions are excluded."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Create source file that should be included
    (repo / "src").mkdir()
    (repo / "src" / "main.py").write_text("print('hello')")

    # Create files with extensions that should be excluded
    excluded_extensions = [
        'module.pyc', 'module.pyo', 'App.class', 'lib.so', 'lib.dll',
        'program.exe', 'lib.dylib', 'code.o', 'code.obj',
        'app.min.js', 'app.bundle.js', 'styles.min.css',
        'debug.log', 'error.log', 'app.log.1',
        'file.bak', 'file.backup', 'file.orig', 'file.tmp',
        'code.generated.cs', 'types.generated.ts'
    ]

    for filename in excluded_extensions:
        (repo / filename).write_text("content")

    # Create coverage files that should be excluded
    (repo / ".coverage").write_text("coverage data")
    (repo / "coverage.xml").write_text("<xml>")
    (repo / "coverage.html").write_text("<html>")

    files = get_canonical_file_list(str(repo))

    # Assert source file is included
    assert any('src/main.py' in p for p in files), "Source files should be included"

    # Assert excluded extensions are not included
    for ext_file in excluded_extensions:
        assert not any(ext_file in p for p in files), f"File '{ext_file}' should be excluded"

    # Assert coverage files are excluded
    assert not any('.coverage' in p for p in files), ".coverage files should be excluded"
    assert not any('coverage.xml' in p for p in files), "coverage.xml should be excluded"
    assert not any('coverage.html' in p for p in files), "coverage.html should be excluded"


def test_excludes_version_control_files(tmp_path):
    """Test that version control system files are excluded."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Create source file
    (repo / "src").mkdir()
    (repo / "src" / "main.py").write_text("print('hello')")

    # Create .git directory with files
    (repo / ".git").mkdir()
    (repo / ".git" / "config").write_text("[core]")
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/main")
    (repo / ".git" / "index").write_text("git index data")

    # Create subdirectory with .git
    (repo / "subdir").mkdir()
    (repo / "subdir" / ".git").mkdir()
    (repo / "subdir" / ".git" / "config").write_text("[core]")
    (repo / "subdir" / "file.txt").write_text("content")

    # Create other VCS directories
    (repo / ".svn").mkdir()
    (repo / ".svn" / "entries").write_text("svn data")
    (repo / ".hg").mkdir()
    (repo / ".hg" / "store").mkdir()
    (repo / ".hg" / "store" / "data").write_text("hg data")

    files = get_canonical_file_list(str(repo))

    # Assert source files are included
    assert any('src/main.py' in p for p in files), "Source files should be included"
    assert any('subdir/file.txt' in p for p in files), "Files outside VCS dirs should be included"

    # Assert VCS files are excluded
    vcs_files = ['.git/config', '.git/HEAD', '.git/index', '.svn/entries', '.hg/store/data']
    for vcs_file in vcs_files:
        assert not any(vcs_file in p for p in files), f"VCS file '{vcs_file}' should be excluded"
