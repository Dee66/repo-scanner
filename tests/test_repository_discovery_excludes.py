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
