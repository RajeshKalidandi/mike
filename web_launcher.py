#!/usr/bin/env python3
"""Launcher script for the Mike Streamlit web interface.

This launcher provides a convenient way to start the web UI with
prerequisite checking and automatic port selection.
"""

import subprocess
import sys
import socket
from pathlib import Path
from typing import Optional


def find_available_port(start_port: int = 8501, max_port: int = 8600) -> int:
    """Find an available port for the web server.

    Args:
        start_port: Starting port number to check
        max_port: Maximum port number to check

    Returns:
        Available port number

    Raises:
        RuntimeError: If no available port found
    """
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                continue

    raise RuntimeError(f"No available ports found between {start_port} and {max_port}")


def check_prerequisites() -> dict:
    """Check if all prerequisites are installed.

    Returns:
        Dictionary with prerequisite status
    """
    status = {
        "streamlit": False,
        "app_exists": False,
        "issues": [],
    }

    # Check if streamlit is installed
    try:
        import streamlit

        status["streamlit"] = True
    except ImportError:
        status["issues"].append("streamlit not installed. Run: pip install streamlit")

    # Check if app exists
    app_path = Path(__file__).parent / "src" / "mike" / "web" / "app.py"
    if app_path.exists():
        status["app_exists"] = True
    else:
        status["issues"].append(f"Web app not found at {app_path}")

    return status


def launch_web_ui(
    port: Optional[int] = None,
    auto_port: bool = True,
    headless: bool = False,
    check_prereqs: bool = True,
) -> int:
    """Launch the Mike web interface.

    Args:
        port: Port to use (auto-selects if None)
        auto_port: Automatically find available port if default is taken
        headless: Run in headless mode (no browser auto-open)
        check_prereqs: Check prerequisites before launching

    Returns:
        Exit code (0 for success, non-zero for failure)

    Example:
        >>> exit_code = launch_web_ui(port=8501)
        >>> if exit_code == 0:
        ...     print("Web UI launched successfully")
    """
    if check_prereqs:
        prereqs = check_prerequisites()
        if prereqs["issues"]:
            print("Prerequisites check failed:")
            for issue in prereqs["issues"]:
                print(f"  ✗ {issue}")
            return 1
        print("✓ Prerequisites check passed")

    # Determine port
    if port is None:
        if auto_port:
            try:
                port = find_available_port()
                print(f"✓ Found available port: {port}")
            except RuntimeError as e:
                print(f"✗ {e}")
                return 1
        else:
            port = 8501

    # Find app path
    app_path = Path(__file__).parent / "src" / "mike" / "web" / "app.py"

    if not app_path.exists():
        print(f"✗ App not found at {app_path}")
        return 1

    # Build streamlit command
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        f"--server.port={port}",
        f"--server.headless={str(headless).lower()}",
        "--browser.gatherUsageStats=false",
    ]

    print(f"\n🚀 Launching Mike Web UI...")
    print(f"   URL: http://localhost:{port}")
    print(f"   Press Ctrl+C to stop\n")

    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except FileNotFoundError:
        print("✗ streamlit not found. Install it with: pip install streamlit")
        return 1
    except subprocess.CalledProcessError as e:
        print(f"✗ Error launching Streamlit: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n✓ Web UI stopped")
        return 0


def main():
    """Main entry point with argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Launch Mike Web Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python web_launcher.py              # Launch with auto port selection
  python web_launcher.py --port 8501  # Launch on specific port
  python web_launcher.py --headless   # Launch without opening browser
        """,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to run the web server on (default: auto-select)",
    )

    parser.add_argument(
        "--no-auto-port",
        action="store_true",
        help="Don't auto-select port if default is taken",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (don't open browser)",
    )

    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip prerequisite checks",
    )

    args = parser.parse_args()

    exit_code = launch_web_ui(
        port=args.port,
        auto_port=not args.no_auto_port,
        headless=args.headless,
        check_prereqs=not args.skip_checks,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
