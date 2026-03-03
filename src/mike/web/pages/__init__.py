"""Web pages for Mike Streamlit UI."""

from mike.web.pages.health import render_health_dashboard
from mike.web.pages.security import render_security_scanner
from mike.web.pages.git import render_git_analytics
from mike.web.pages.patch import render_patch_manager

__all__ = [
    "render_health_dashboard",
    "render_security_scanner",
    "render_git_analytics",
    "render_patch_manager",
]
