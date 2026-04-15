"""Git repository cloning utilities."""

import re
import subprocess
from pathlib import Path
from typing import Optional


def is_git_url(url: str) -> bool:
    """Check if URL is a git repository URL.

    Supports both standard git URLs and GitHub web URLs (with or without .git suffix).

    Args:
        url: URL to check

    Returns:
        True if URL looks like a git repository URL
    """
    # Standard git URL patterns
    git_patterns = [
        r"^git@.+:.+\.git$",  # SSH format: git@github.com:user/repo.git
        r"^https?://.+\.git$",  # HTTPS format: https://github.com/user/repo.git
        r"^git://.+\.git$",  # Git protocol
        r"^ssh://.+\.git$",  # SSH protocol
    ]

    # GitHub web URL patterns (without .git suffix)
    github_patterns = [
        r"^https?://github\.com/[^/]+/[^/]+/?$",  # https://github.com/user/repo
    ]

    all_patterns = git_patterns + github_patterns
    return any(re.match(pattern, url) for pattern in all_patterns)


def clone_repository(
    repo_url: str,
    target_dir: Optional[str] = None,
    branch: Optional[str] = None,
    depth: int = 1,
) -> str:
    """Clone a git repository.

    Args:
        repo_url: URL of the repository to clone
        target_dir: Directory to clone into (default: repo name)
        branch: Branch to checkout (default: default branch)
        depth: Clone depth for shallow clone (default: 1)

    Returns:
        Path to the cloned repository

    Raises:
        RuntimeError: If cloning fails
    """
    if not is_git_url(repo_url):
        raise ValueError(f"Not a valid git URL: {repo_url}")

    # Convert GitHub web URL to git URL if needed
    if "github.com" in repo_url and not repo_url.endswith(".git"):
        repo_url = repo_url.rstrip("/") + ".git"

    # Determine target directory
    if target_dir is None:
        # Extract repo name from URL (handle both .git and non-.git URLs)
        match = re.search(r"/([^/]+?)(?:\.git)?$", repo_url)
        if match:
            target_dir_name = match.group(1)
        else:
            raise ValueError(f"Could not extract repo name from URL: {repo_url}")
    else:
        target_dir_name = target_dir

    target_path = Path(target_dir_name).resolve()

    # Build git clone command
    cmd = ["git", "clone"]

    if depth is not None:
        cmd.extend(["--depth", str(depth)])

    if branch is not None:
        cmd.extend(["--branch", branch])

    cmd.extend([repo_url, str(target_path)])

    # Execute clone
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return str(target_path)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to clone repository: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("git command not found. Please install git.")
