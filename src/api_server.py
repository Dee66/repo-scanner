"""Public API server entrypoint for tests.

Exposes the FastAPI application (and supporting attributes) defined in
src.optional.api_server so integration tests can import `src.api_server`
without falling back to a blank FastAPI app.
"""

from src.optional import api_server as _api_server

app = _api_server.app
git = _api_server.git
tempfile = _api_server.tempfile
execute_pipeline = getattr(_api_server, "execute_pipeline", None)

__all__ = ["app"]
