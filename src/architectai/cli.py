"""CLI entry point for ArchitectAI."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

import click

from architectai.db.models import Database
from architectai.scanner.scanner import FileScanner
from architectai.scanner.clone import clone_repository
from architectai.parser.parser import ASTParser


def get_default_db_path() -> str:
    """Get default database path."""
    home = Path.home()
    db_dir = home / ".architectai"
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / "architectai.db")


@click.group()
@click.option(
    "--db",
    default=get_default_db_path,
    help="Database file path",
    type=click.Path(),
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def main(ctx: click.Context, db: str, verbose: bool) -> None:
    """ArchitectAI - Local AI Software Architect for Codebases."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db
    ctx.obj["verbose"] = verbose


@main.command()
@click.argument("source")
@click.option("--session-name", "-n", help="Session name")
@click.pass_context
def scan(ctx: click.Context, source: str, session_name: Optional[str]) -> None:
    """Scan a codebase directory or git repository."""
    db_path = ctx.obj["db_path"]
    verbose = ctx.obj["verbose"]

    # Initialize database
    db = Database(db_path)
    db.init()

    # Check if source is a git URL or local path
    is_git_url = source.startswith("http") or source.startswith("git@")
    temp_dir = None

    try:
        if is_git_url:
            if verbose:
                click.echo(f"Cloning repository: {source}")
            temp_dir = tempfile.mkdtemp(prefix="architectai_")
            clone_path = clone_repository(source, temp_dir)
            if clone_path is None:
                click.echo("Error: Failed to clone repository", err=True)
                sys.exit(1)
            scan_path = clone_path
            source_path = source
        else:
            scan_path = os.path.abspath(source)
            if not os.path.exists(scan_path):
                click.echo(f"Error: Path not found: {source}", err=True)
                sys.exit(1)
            source_path = scan_path

        # Create session
        session_id = db.create_session(
            source_path=source_path,
            session_type="git" if is_git_url else "local",
        )

        if verbose:
            click.echo(f"Created session: {session_id}")

        # Scan directory
        scanner = FileScanner()
        files = scanner.scan_directory(scan_path)

        if verbose:
            click.echo(f"Found {len(files)} files")

        # Insert files into database
        for file_info in files:
            db.insert_file(
                session_id=session_id,
                relative_path=file_info["relative_path"],
                absolute_path=file_info["absolute_path"],
                language=file_info["language"],
                size_bytes=file_info["size_bytes"],
                line_count=file_info["line_count"],
                content_hash=file_info["content_hash"],
            )

        # Print summary
        click.echo(f"Scanned {len(files)} files")
        click.echo(f"Session ID: {session_id}")

        # Show language breakdown
        if files:
            languages = {}
            for f in files:
                lang = f["language"]
                languages[lang] = languages.get(lang, 0) + 1

            click.echo("\nLanguage breakdown:")
            for lang, count in sorted(languages.items(), key=lambda x: -x[1]):
                click.echo(f"  {lang}: {count} files")

    finally:
        # Cleanup temp directory if we cloned
        if temp_dir and os.path.exists(temp_dir):
            import shutil

            shutil.rmtree(temp_dir)


@main.command()
@click.argument("session_id")
@click.pass_context
def parse(ctx: click.Context, session_id: str) -> None:
    """Parse code in a session."""
    db_path = ctx.obj["db_path"]
    verbose = ctx.obj["verbose"]

    # Initialize database
    db = Database(db_path)
    db.init()

    # Get session
    session = db.get_session(session_id)
    if session is None:
        click.echo(f"Error: Session not found: {session_id}", err=True)
        sys.exit(1)

    if verbose:
        click.echo(f"Parsing session: {session_id}")

    # Get all files for session
    files = db.get_files_for_session(session_id)

    if not files:
        click.echo("No files found in session")
        return

    # Parse each file
    parser = ASTParser()
    parsed_count = 0
    error_count = 0

    for file_record in files:
        try:
            # Read file content
            file_path = file_record["absolute_path"]
            if not os.path.exists(file_path):
                continue

            content = Path(file_path).read_text(encoding="utf-8")
            language = file_record["language"]

            # Parse the file
            result = parser.parse(content, language)

            # Update database with parsing status
            db.update_file_parsed(
                file_id=file_record["id"],
                ast_available=True,
            )

            parsed_count += 1

            if verbose:
                func_count = len(result.get("functions", []))
                class_count = len(result.get("classes", []))
                click.echo(
                    f"  {file_record['relative_path']}: {func_count} functions, {class_count} classes"
                )

        except Exception as e:
            if verbose:
                click.echo(
                    f"  Error parsing {file_record['relative_path']}: {e}", err=True
                )
            error_count += 1

    click.echo(f"Parsed {parsed_count} files")
    if error_count > 0:
        click.echo(f"Errors: {error_count}")


@main.command("list-sessions")
@click.pass_context
def list_sessions(ctx: click.Context) -> None:
    """List all sessions."""
    db_path = ctx.obj["db_path"]

    # Initialize database
    db = Database(db_path)
    db.init()

    # For now, just show a placeholder message
    # In a full implementation, we would query all sessions from the database
    click.echo("Sessions:")
    click.echo(
        "  (Session listing will be implemented with session query functionality)"
    )
