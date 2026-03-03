"""CLI entry point for Mike."""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

import click

from mike.db.models import Database
from mike.scanner.scanner import FileScanner
from mike.scanner.clone import clone_repository
from mike.parser.parser import ASTParser
from mike.cli_orchestrator import Orchestrator, TaskProgress
from mike.config.commands import get_config_group
from mike.monitoring.telemetry import TelemetryCollector
from mike.monitoring.metrics import MetricsRegistry
from mike.monitoring.reporter import (
    ConsoleReporter,
    JsonReporter,
    MarkdownReporter,
    ReportGenerator,
)
from mike.monitoring.dashboard import DashboardGenerator


def get_default_db_path() -> str:
    """Get default database path."""
    home = Path.home()
    db_dir = home / ".mike"
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / "mike.db")


def format_output(
    data: dict, format_type: str, plain_template: Optional[str] = None
) -> str:
    """Format output based on format type."""
    if format_type == "json":
        return json.dumps(data, indent=2, default=str)
    elif format_type == "markdown":
        if isinstance(data, dict):
            return dict_to_markdown(data)
        return str(data)
    else:
        if plain_template:
            return plain_template
        return str(data)


def dict_to_markdown(data: dict, level: int = 1) -> str:
    """Convert dictionary to markdown."""
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{'#' * level} {key.title()}")
            lines.append(dict_to_markdown(value, level + 1))
        elif isinstance(value, list):
            lines.append(f"{'#' * level} {key.title()}")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"- {item.get('name', item)}")
                    for k, v in item.items():
                        if k != "name":
                            lines.append(f"  - {k}: {v}")
                else:
                    lines.append(f"- {item}")
        else:
            lines.append(f"**{key}:** {value}")
        lines.append("")
    return "\n".join(lines)


@click.group()
@click.option(
    "--db",
    default=get_default_db_path,
    help="Database file path",
    type=click.Path(),
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option(
    "--output",
    "-o",
    default="plain",
    type=click.Choice(["plain", "json", "markdown"]),
    help="Output format",
)
@click.pass_context
def main(ctx: click.Context, db: str, verbose: bool, output: str) -> None:
    """Mike - Local AI Software Architect for Codebases."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db
    ctx.obj["verbose"] = verbose
    ctx.obj["output_format"] = output


@main.command()
@click.argument("source")
@click.option("--session-name", "-n", help="Session name")
@click.pass_context
def scan(ctx: click.Context, source: str, session_name: Optional[str]) -> None:
    """Scan a codebase directory or git repository."""
    db_path = ctx.obj["db_path"]
    verbose = ctx.obj["verbose"]
    output_format = ctx.obj["output_format"]

    db = Database(db_path)
    db.init()

    is_git_url = source.startswith("http") or source.startswith("git@")
    temp_dir = None

    try:
        if is_git_url:
            if verbose:
                click.echo(f"Cloning repository: {source}")
            temp_dir = tempfile.mkdtemp(prefix="mike_")
            clone_path = clone_repository(source, temp_dir)
            if clone_path is None:
                error_msg = "Error: Failed to clone repository"
                if output_format == "json":
                    click.echo(json.dumps({"error": error_msg}))
                else:
                    click.echo(error_msg, err=True)
                sys.exit(1)
            scan_path = clone_path
            source_path = source
        else:
            scan_path = os.path.abspath(source)
            if not os.path.exists(scan_path):
                error_msg = f"Error: Path not found: {source}"
                if output_format == "json":
                    click.echo(json.dumps({"error": error_msg}))
                else:
                    click.echo(error_msg, err=True)
                sys.exit(1)
            source_path = scan_path

        session_id = db.create_session(
            source_path=source_path,
            session_type="git" if is_git_url else "local",
        )

        if verbose:
            click.echo(f"Created session: {session_id}")

        scanner = FileScanner()
        files = scanner.scan_directory(scan_path)

        if verbose:
            click.echo(f"Found {len(files)} files")

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

        languages = {}
        for f in files:
            lang = f["language"]
            languages[lang] = languages.get(lang, 0) + 1

        result = {
            "session_id": session_id,
            "files_scanned": len(files),
            "source": source_path,
            "languages": languages,
        }

        if output_format == "json":
            click.echo(json.dumps(result, indent=2))
        elif output_format == "markdown":
            click.echo(f"# Scan Results\n")
            click.echo(f"**Session ID:** {session_id}\n")
            click.echo(f"**Files Scanned:** {len(files)}\n")
            click.echo(f"## Languages\n")
            for lang, count in sorted(languages.items(), key=lambda x: -x[1]):
                click.echo(f"- {lang}: {count} files")
        else:
            click.echo(f"Scanned {len(files)} files")
            click.echo(f"Session ID: {session_id}")
            if files:
                click.echo("\nLanguage breakdown:")
                for lang, count in sorted(languages.items(), key=lambda x: -x[1]):
                    click.echo(f"  {lang}: {count} files")

    finally:
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
    output_format = ctx.obj["output_format"]

    db = Database(db_path)
    db.init()

    session = db.get_session(session_id)
    if session is None:
        error_msg = f"Error: Session not found: {session_id}"
        if output_format == "json":
            click.echo(json.dumps({"error": error_msg}))
        else:
            click.echo(error_msg, err=True)
        sys.exit(1)

    if verbose:
        click.echo(f"Parsing session: {session_id}")

    files = db.get_files_for_session(session_id)

    if not files:
        msg = "No files found in session"
        if output_format == "json":
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(msg)
        return

    parser = ASTParser()
    parsed_count = 0
    error_count = 0

    for file_record in files:
        try:
            file_path = file_record["absolute_path"]
            if not os.path.exists(file_path):
                continue

            content = Path(file_path).read_text(encoding="utf-8")
            language = file_record["language"]

            result = parser.parse(content, language)

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

    result = {
        "session_id": session_id,
        "parsed": parsed_count,
        "errors": error_count,
        "total": len(files),
    }

    if output_format == "json":
        click.echo(json.dumps(result, indent=2))
    elif output_format == "markdown":
        click.echo(f"# Parse Results\n")
        click.echo(f"**Session ID:** {session_id}\n")
        click.echo(f"**Parsed:** {parsed_count}/{len(files)} files\n")
        if error_count > 0:
            click.echo(f"**Errors:** {error_count}\n")
    else:
        click.echo(f"Parsed {parsed_count} files")
        if error_count > 0:
            click.echo(f"Errors: {error_count}")


@main.command()
@click.argument("session_id")
@click.option("--output", "-o", default=None, help="Output directory for documentation")
@click.option(
    "--type",
    "doc_type",
    multiple=True,
    default=["readme", "architecture"],
    type=click.Choice(["readme", "architecture", "api", "env"]),
    help="Types of documentation to generate",
)
@click.pass_context
def docs(
    ctx: click.Context, session_id: str, output: Optional[str], doc_type: tuple
) -> None:
    """Generate documentation for a session."""
    db_path = ctx.obj["db_path"]
    verbose = ctx.obj["verbose"]
    output_format = ctx.obj["output_format"]

    orchestrator = Orchestrator(db_path, verbose=verbose)

    progress_shown = False
    result = None

    for progress in orchestrator.generate_documentation(
        session_id=session_id,
        output_dir=output,
        doc_types=list(doc_type),
    ):
        if verbose:
            click.echo(f"[{progress.status.upper()}] {progress.message}")
        elif not progress_shown and progress.status == "running":
            click.echo("Generating documentation...", nl=False)
            progress_shown = True

        if progress.status in ["completed", "failed"]:
            result = progress.result if hasattr(progress, "result") else None
            if progress_shown:
                click.echo(f" {progress.status}")

            if progress.status == "failed" and progress.error:
                if output_format == "json":
                    click.echo(json.dumps({"error": progress.error}))
                else:
                    click.echo(f"Error: {progress.error}", err=True)
                sys.exit(1)

    if result:
        if output_format == "json":
            click.echo(json.dumps(result, indent=2, default=str))
        elif output_format == "markdown":
            click.echo(f"# Documentation Generated\n")
            if isinstance(result, dict):
                if "output_dir" in result:
                    click.echo(f"**Output Directory:** `{result['output_dir']}`\n")
                if "files_generated" in result:
                    click.echo(f"## Files Generated\n")
                    for f in result["files_generated"]:
                        click.echo(f"- {f}")
        else:
            if isinstance(result, dict) and "output_dir" in result:
                click.echo(f"Documentation generated in: {result['output_dir']}")


@main.command()
@click.argument("session_id")
@click.argument("question")
@click.pass_context
def ask(ctx: click.Context, session_id: str, question: str) -> None:
    """Ask a question about the codebase."""
    db_path = ctx.obj["db_path"]
    verbose = ctx.obj["verbose"]
    output_format = ctx.obj["output_format"]

    orchestrator = Orchestrator(db_path, verbose=verbose)

    result_data = None

    for progress in orchestrator.ask_question(session_id=session_id, question=question):
        if verbose:
            click.echo(f"[{progress.status.upper()}] {progress.message}")

        if progress.status in ["completed", "failed"]:
            if progress.status == "failed" and progress.error:
                if output_format == "json":
                    click.echo(json.dumps({"error": progress.error}))
                else:
                    click.echo(f"Error: {progress.error}", err=True)
                sys.exit(1)

            if progress.result and isinstance(progress.result, dict):
                result_data = progress.result

    if result_data and "answer" in result_data:
        if output_format == "json":
            click.echo(json.dumps(result_data, indent=2))
        elif output_format == "markdown":
            click.echo(f"# Q&A\n")
            click.echo(f"**Question:** {result_data.get('question', question)}\n")
            click.echo(f"## Answer\n")
            click.echo(result_data["answer"])
            if "relevant_files" in result_data and result_data["relevant_files"]:
                click.echo(f"\n## Relevant Files\n")
                for f in result_data["relevant_files"]:
                    click.echo(f"- `{f}`")
        else:
            click.echo(result_data["answer"])
    else:
        click.echo("No answer generated.")


@main.command()
@click.argument("session_id")
@click.option(
    "--focus",
    "-f",
    multiple=True,
    type=click.Choice(["performance", "readability", "structure", "security"]),
    help="Focus areas for refactoring analysis",
)
@click.pass_context
def refactor(ctx: click.Context, session_id: str, focus: tuple) -> None:
    """Analyze code and suggest refactoring improvements."""
    db_path = ctx.obj["db_path"]
    verbose = ctx.obj["verbose"]
    output_format = ctx.obj["output_format"]

    orchestrator = Orchestrator(db_path, verbose=verbose)

    focus_areas = list(focus) if focus else None
    result_data = None

    for progress in orchestrator.analyze_refactoring(
        session_id=session_id,
        focus_areas=focus_areas,
    ):
        if verbose:
            click.echo(f"[{progress.status.upper()}] {progress.message}")

        if progress.status == "completed":
            if isinstance(progress.result, dict):
                result_data = progress.result

    if result_data:
        if output_format == "json":
            click.echo(json.dumps(result_data, indent=2, default=str))
        elif output_format == "markdown":
            click.echo(f"# Refactoring Analysis\n")
            if "suggestions" in result_data:
                click.echo(f"## Suggestions ({len(result_data['suggestions'])})\n")
                for i, suggestion in enumerate(result_data["suggestions"], 1):
                    click.echo(
                        f"### {i}. {suggestion.get('type', 'General').replace('_', ' ').title()}\n"
                    )
                    click.echo(f"{suggestion.get('description', '')}\n")
                    if "recommendation" in suggestion:
                        click.echo(
                            f"**Recommendation:** {suggestion['recommendation']}\n"
                        )
        else:
            if "suggestions" in result_data:
                click.echo(f"Found {len(result_data['suggestions'])} suggestions:")
                for suggestion in result_data["suggestions"]:
                    click.echo(f"\n[{suggestion.get('type', 'unknown').upper()}]")
                    click.echo(f"  {suggestion.get('description', '')}")
                    if "recommendation" in suggestion:
                        click.echo(f"  Recommendation: {suggestion['recommendation']}")


@main.command()
@click.argument("template_session_id")
@click.argument("output_dir")
@click.option(
    "--constraint",
    "-c",
    multiple=True,
    help="Constraints for rebuilding (key=value format)",
)
@click.pass_context
def rebuild(
    ctx: click.Context, template_session_id: str, output_dir: str, constraint: tuple
) -> None:
    """Scaffold a new project from a template session."""
    db_path = ctx.obj["db_path"]
    verbose = ctx.obj["verbose"]
    output_format = ctx.obj["output_format"]

    orchestrator = Orchestrator(db_path, verbose=verbose)

    constraints = {}
    for c in constraint:
        if "=" in c:
            key, value = c.split("=", 1)
            constraints[key] = value

    result_data = None

    for progress in orchestrator.rebuild_project(
        template_session_id=template_session_id,
        output_dir=output_dir,
        constraints=constraints if constraints else None,
    ):
        if verbose:
            click.echo(f"[{progress.status.upper()}] {progress.message}")

        if progress.status == "completed":
            if isinstance(progress.result, dict):
                result_data = progress.result

    if result_data:
        if output_format == "json":
            click.echo(json.dumps(result_data, indent=2, default=str))
        elif output_format == "markdown":
            click.echo(f"# Project Scaffolded\n")
            if "output_dir" in result_data:
                click.echo(f"**Output Directory:** `{result_data['output_dir']}`\n")
            if "files_created" in result_data:
                click.echo(f"**Files Created:** {len(result_data['files_created'])}\n")
        else:
            click.echo(f"Project scaffolded in: {output_dir}")
            if "files_created" in result_data:
                click.echo(f"Created {result_data['files_created']} files")


@main.group()
def session():
    """Manage sessions."""
    pass


@session.command("list")
@click.option("--limit", "-l", default=20, help="Maximum number of sessions to show")
@click.pass_context
def session_list(ctx: click.Context, limit: int) -> None:
    """List all sessions."""
    db_path = ctx.obj["db_path"]
    output_format = ctx.obj["output_format"]

    orchestrator = Orchestrator(db_path)
    sessions = orchestrator.list_sessions()

    sessions = sessions[:limit]

    if output_format == "json":
        click.echo(
            json.dumps(
                [
                    {
                        "id": s.session_id,
                        "source": s.source_path,
                        "type": s.session_type,
                        "status": s.status,
                        "created": s.created_at,
                    }
                    for s in sessions
                ],
                indent=2,
            )
        )
    elif output_format == "markdown":
        click.echo(f"# Sessions ({len(sessions)})\n")
        click.echo("| ID | Source | Type | Status | Created |")
        click.echo("|---|---|---|---|---|")
        for s in sessions:
            click.echo(
                f"| {s.session_id[:8]}... | {s.source_path[:30]}... | {s.session_type} | {s.status} | {s.created_at[:10]} |"
            )
    else:
        if not sessions:
            click.echo("No sessions found.")
            return

        click.echo(f"Sessions ({len(sessions)}):\n")
        for s in sessions:
            click.echo(
                f"  {s.session_id[:8]}...  {s.source_path[:40]:<40}  {s.session_type:8}  {s.status:10}  {s.created_at[:16]}"
            )


@session.command("info")
@click.argument("session_id")
@click.pass_context
def session_info(ctx: click.Context, session_id: str) -> None:
    """Show detailed information about a session."""
    db_path = ctx.obj["db_path"]
    output_format = ctx.obj["output_format"]

    orchestrator = Orchestrator(db_path)
    session = orchestrator.get_session(session_id)

    if session is None:
        error_msg = f"Session not found: {session_id}"
        if output_format == "json":
            click.echo(json.dumps({"error": error_msg}))
        else:
            click.echo(error_msg, err=True)
        sys.exit(1)

    stats = orchestrator.get_session_stats(session_id)

    result = {
        "session_id": session.session_id,
        "source_path": session.source_path,
        "session_type": session.session_type,
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "stats": stats,
    }

    if output_format == "json":
        click.echo(json.dumps(result, indent=2, default=str))
    elif output_format == "markdown":
        click.echo(f"# Session Information\n")
        click.echo(f"**Session ID:** {session.session_id}\n")
        click.echo(f"**Source:** `{session.source_path}`\n")
        click.echo(f"**Type:** {session.session_type}\n")
        click.echo(f"**Status:** {session.status}\n")
        click.echo(f"**Created:** {session.created_at}\n")
        click.echo(f"## Statistics\n")
        click.echo(f"- Files: {stats.get('file_count', 0)}")
        click.echo(f"- Parsed: {stats.get('parsed_count', 0)}")
        click.echo(f"- Total Lines: {stats.get('total_lines', 0)}")
        if stats.get("languages"):
            click.echo(f"\n## Languages\n")
            for lang, count in sorted(stats["languages"].items(), key=lambda x: -x[1]):
                click.echo(f"- {lang}: {count} files")
    else:
        click.echo(f"Session: {session.session_id}")
        click.echo(f"Source: {session.source_path}")
        click.echo(f"Type: {session.session_type}")
        click.echo(f"Status: {session.status}")
        click.echo(f"Created: {session.created_at}")
        click.echo(f"\nStatistics:")
        click.echo(f"  Files: {stats.get('file_count', 0)}")
        click.echo(f"  Parsed: {stats.get('parsed_count', 0)}")
        click.echo(f"  Total Lines: {stats.get('total_lines', 0)}")
        if stats.get("languages"):
            click.echo(f"\nLanguages:")
            for lang, count in sorted(stats["languages"].items(), key=lambda x: -x[1])[
                :10
            ]:
                click.echo(f"  {lang}: {count} files")


@session.command("delete")
@click.argument("session_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.pass_context
def session_delete(ctx: click.Context, session_id: str, force: bool) -> None:
    """Delete a session."""
    db_path = ctx.obj["db_path"]
    output_format = ctx.obj["output_format"]

    orchestrator = Orchestrator(db_path)
    session = orchestrator.get_session(session_id)

    if session is None:
        error_msg = f"Session not found: {session_id}"
        if output_format == "json":
            click.echo(json.dumps({"error": error_msg}))
        else:
            click.echo(error_msg, err=True)
        sys.exit(1)

    if not force:
        if not click.confirm(f"Delete session {session_id[:8]}...?"):
            click.echo("Aborted.")
            return

    success = orchestrator.delete_session(session_id)

    if success:
        msg = f"Session {session_id[:8]}... deleted."
        if output_format == "json":
            click.echo(json.dumps({"success": True, "message": msg}))
        else:
            click.echo(msg)
    else:
        msg = "Failed to delete session."
        if output_format == "json":
            click.echo(json.dumps({"error": msg}))
        else:
            click.echo(msg, err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show system status and available models."""
    db_path = ctx.obj["db_path"]
    output_format = ctx.obj["output_format"]

    orchestrator = Orchestrator(db_path)
    system_status = orchestrator.get_system_status()

    if output_format == "json":
        click.echo(json.dumps(system_status, indent=2, default=str))
    elif output_format == "markdown":
        click.echo(f"# System Status\n")
        click.echo(f"**Version:** {system_status.get('version', 'unknown')}\n")
        click.echo(f"**Database:** `{system_status.get('database_path', 'unknown')}`\n")
        click.echo(f"**Sessions:** {system_status.get('session_count', 0)}\n")
        click.echo(f"## Agents\n")
        for name, info in system_status.get("agents", {}).items():
            status_icon = "✅" if info.get("status") == "available" else "❌"
            click.echo(f"- {status_icon} **{name}:** {info.get('description', '')}")
        click.echo(f"\n## Models\n")
        for model in system_status.get("available_models", []):
            click.echo(
                f"- **{model.get('name', 'unknown')}:** {model.get('description', '')} ({model.get('status', 'unknown')})"
            )
    else:
        click.echo(f"Mike v{system_status.get('version', 'unknown')}")
        click.echo(f"Database: {system_status.get('database_path', 'unknown')}")
        click.echo(f"Sessions: {system_status.get('session_count', 0)}")
        click.echo(f"\nAgents:")
        for name, info in system_status.get("agents", {}).items():
            status_icon = "✓" if info.get("status") == "available" else "✗"
            click.echo(f"  [{status_icon}] {name:12} - {info.get('description', '')}")
        click.echo(f"\nModels:")
        for model in system_status.get("available_models", []):
            click.echo(
                f"  - {model.get('name', 'unknown')}: {model.get('description', '')}"
            )


@main.command()
@click.argument("session_id")
@click.option("--output", "-o", help="Output file for graph export (JSON)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def build_graph(
    ctx: click.Context, session_id: str, output: str, verbose: bool
):
    """Build dependency graph from parsed session files."""
    db_path = ctx.obj["db_path"]
    output_format = ctx.obj["output_format"]

    if verbose:
        click.echo(f"Building graph for session: {session_id}")

    from mike.pipeline.graph_pipeline import GraphPipeline

    try:
        db = Database(db_path)
        pipeline = GraphPipeline(db)

        click.echo("Analyzing imports and building dependency graph...")
        graph = pipeline.build_from_session(session_id)

        stats = graph.get_graph_stats()
        click.echo(
            f"Graph built: {stats['nodes']} files, {stats['edges']} dependencies"
        )

        cycles = graph.find_cycles()
        if cycles:
            click.echo(f"Warning: Found {len(cycles)} circular dependencies")
            if verbose:
                for cycle in cycles:
                    click.echo(f"  Cycle: {' -> '.join(cycle)}")

        if output:
            graph_dict = graph.export_to_dict()
            with open(output, "w") as f:
                json.dump(graph_dict, f, indent=2)
            click.echo(f"Graph exported to {output}")

    except Exception as e:
        error_msg = f"Error: {e}"
        if output_format == "json":
            click.echo(json.dumps({"error": error_msg}))
        else:
            click.echo(error_msg, err=True)
        sys.exit(1)


@main.command()
@click.argument("session_id")
@click.option("--model", default="mxbai-embed-large", help="Embedding model to use")
@click.option(
    "--vector-dir", default="./vector_store", help="Directory for vector store"
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def embed(
    ctx: click.Context,
    session_id: str,
    model: str,
    vector_dir: str,
    verbose: bool,
):
    """Generate embeddings and store in vector database."""
    db_path = ctx.obj["db_path"]
    output_format = ctx.obj["output_format"]

    if verbose:
        click.echo(f"Embedding session: {session_id}")
        click.echo(f"Using model: {model}")

    from mike.chunker.chunker import CodeChunker
    from mike.embeddings.service import EmbeddingService
    from mike.vectorstore.store import VectorStore

    try:
        db = Database(db_path)
        chunker = CodeChunker(chunk_size=1000, chunk_overlap=200)
        embed_service = EmbeddingService(model=model)

        os.makedirs(vector_dir, exist_ok=True)
        vector_store = VectorStore(vector_dir)

        if not embed_service.check_model_available():
            msg = f"Warning: Model {model} not found in Ollama"
            click.echo(msg)
            click.echo("Please run: ollama pull " + model)
            return

        files = db.get_files_for_session(session_id)

        if not files:
            click.echo("No files found in session")
            return

        click.echo(f"Processing {len(files)} files...")

        all_chunks = []
        for row in files:
            file_path = row["absolute_path"]
            relative_path = row["relative_path"]
            language = row["language"]

            if verbose:
                click.echo(f"  Chunking: {relative_path}")

            try:
                chunks = chunker.chunk_file(file_path, language)
                for chunk in chunks:
                    chunk["metadata"]["file_path"] = relative_path
                    chunk["metadata"]["language"] = language
                    chunk["metadata"]["session_id"] = session_id
                all_chunks.extend(chunks)
            except Exception as e:
                if verbose:
                    click.echo(f"    Error chunking: {e}")

        click.echo(f"Generated {len(all_chunks)} chunks")

        if not all_chunks:
            click.echo("No chunks to embed")
            return

        click.echo("Generating embeddings...")
        chunks_with_embeddings = embed_service.embed_chunks(all_chunks)

        click.echo("Storing in vector database...")
        vector_store.add_chunks(chunks_with_embeddings, session_id)

        count = vector_store.count(session_id)
        click.echo(f"Successfully stored {count} chunks in vector store")

    except Exception as e:
        error_msg = f"Error: {e}"
        if output_format == "json":
            click.echo(json.dumps({"error": error_msg}))
        else:
            click.echo(error_msg, err=True)
        sys.exit(1)


@main.command()
@click.argument("session_id")
@click.argument("query")
@click.option(
    "--vector-dir", default="./vector_store", help="Directory for vector store"
)
@click.option("--model", default="mxbai-embed-large", help="Embedding model to use")
@click.option("--n-results", default=5, help="Number of results")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def search(
    ctx: click.Context,
    session_id: str,
    query: str,
    vector_dir: str,
    model: str,
    n_results: int,
    verbose: bool,
):
    """Search for code using natural language query."""
    output_format = ctx.obj["output_format"]

    if verbose:
        click.echo(f"Searching: {query}")

    from mike.embeddings.service import EmbeddingService
    from mike.vectorstore.store import VectorStore

    try:
        embed_service = EmbeddingService(model=model)
        vector_store = VectorStore(vector_dir)

        if session_id not in vector_store.list_sessions():
            click.echo(f"Session {session_id} not found in vector store")
            click.echo("Run 'mike embed' first")
            return

        results = vector_store.search_by_text(
            query, embed_service, session_id, n_results
        )

        if not results:
            click.echo("No results found")
            return

        if output_format == "json":
            click.echo(json.dumps({"results": results}, indent=2, default=str))
        elif output_format == "markdown":
            click.echo(f"# Search Results\n")
            click.echo(f"**Query:** {query}\n")
            click.echo(f"**Found:** {len(results)} results\n")
            for i, result in enumerate(results, 1):
                metadata = result.get("metadata", {})
                file_path = metadata.get("file_path", "unknown")
                score = result.get("distance", 0)
                click.echo(f"## {i}. {file_path} (score: {score:.3f})\n")
                content = result.get("content", "")
                click.echo(f"```\n{content[:500]}\n```\n")
        else:
            click.echo(f"\nFound {len(results)} results:\n")

            for i, result in enumerate(results, 1):
                metadata = result.get("metadata", {})
                file_path = metadata.get("file_path", "unknown")
                score = result.get("distance", 0)

                click.echo(f"{i}. {file_path} (score: {score:.3f})")

                content = result.get("content", "")
                lines = content.split("\n")[:3]
                for line in lines:
                    click.echo(f"   {line}")
                if len(content.split("\n")) > 3:
                    click.echo("   ...")
                click.echo()

    except Exception as e:
        error_msg = f"Error: {e}"
        if output_format == "json":
            click.echo(json.dumps({"error": error_msg}))
        else:
            click.echo(error_msg, err=True)
        sys.exit(1)


@main.command("list-sessions")
@click.pass_context
def list_sessions_legacy(ctx: click.Context) -> None:
    """List all sessions (deprecated, use 'session list')."""
    click.echo(
        "Note: 'list-sessions' is deprecated. Use 'session list' instead.", err=True
    )
    ctx.invoke(session_list)


# Add config commands
main.add_command(get_config_group())


@main.group()
def telemetry():
    """Telemetry and monitoring commands."""
    pass


@telemetry.command("stats")
@click.option(
    "--session",
    "session_id",
    help="Show statistics for a specific session",
)
@click.option(
    "--format",
    "output_format_opt",
    type=click.Choice(["plain", "json", "markdown"]),
    help="Output format (overrides global --output)",
)
@click.pass_context
def telemetry_stats(
    ctx: click.Context, session_id: Optional[str], output_format_opt: Optional[str]
) -> None:
    """Show system telemetry statistics."""
    output_format = output_format_opt or ctx.obj.get("output_format", "plain")

    collector = TelemetryCollector()
    registry = MetricsRegistry()

    try:
        if session_id:
            stats = collector.get_session_stats(session_id)
        else:
            stats = collector.get_system_stats()

        if output_format == "json":
            click.echo(json.dumps(stats, indent=2))
        elif output_format == "markdown":
            click.echo("# Telemetry Statistics\n")
            click.echo("| Metric | Value |")
            click.echo("|--------|-------|")
            for key, value in stats.items():
                if isinstance(value, float):
                    value = f"{value:.2f}"
                click.echo(f"| {key} | {value} |")
        else:
            click.echo("Telemetry Statistics:")
            click.echo("")
            for key, value in stats.items():
                if isinstance(value, float):
                    value = f"{value:.2f}"
                click.echo(f"  {key}: {value}")
    except Exception as e:
        if output_format == "json":
            click.echo(json.dumps({"error": str(e)}))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@telemetry.command("report")
@click.option(
    "--session",
    "session_id",
    help="Generate report for a specific session",
)
@click.option(
    "--format",
    "report_format",
    default="markdown",
    type=click.Choice(["console", "json", "markdown"]),
    help="Report format",
)
@click.option(
    "--output",
    "-o",
    help="Output file path (optional, defaults to stdout)",
)
@click.pass_context
def telemetry_report(
    ctx: click.Context,
    session_id: Optional[str],
    report_format: str,
    output: Optional[str],
) -> None:
    """Generate telemetry report."""
    collector = TelemetryCollector()
    registry = MetricsRegistry()

    try:
        if report_format == "json":
            reporter = JsonReporter(collector, registry)
        elif report_format == "markdown":
            reporter = MarkdownReporter(collector, registry)
        else:
            reporter = ConsoleReporter(collector, registry)

        content = reporter.generate_report(session_id=session_id)

        if output:
            with open(output, "w") as f:
                f.write(content)
            click.echo(f"Report saved to: {output}")
        else:
            click.echo(content)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@telemetry.command("dashboard")
@click.option(
    "--output",
    "-o",
    default="dashboard.html",
    help="Output path for dashboard HTML file",
)
@click.option(
    "--serve",
    is_flag=True,
    help="Start HTTP server to serve the dashboard",
)
@click.option(
    "--port",
    default=8080,
    help="Port for HTTP server (requires --serve)",
)
def telemetry_dashboard(output: str, serve: bool, port: int) -> None:
    """Generate and optionally serve monitoring dashboard."""
    try:
        generator = DashboardGenerator()

        if serve:
            generator.serve_dashboard(port=port, dashboard_path=output)
        else:
            path = generator.generate_dashboard(output)
            click.echo(f"Dashboard generated: {path}")
            click.echo("Open the file in a web browser to view.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@telemetry.command("metrics")
@click.option(
    "--format",
    default="plain",
    type=click.Choice(["plain", "json", "prometheus"]),
    help="Output format",
)
def telemetry_metrics(format: str) -> None:
    """Show current metrics."""
    registry = MetricsRegistry()

    try:
        if format == "json":
            click.echo(json.dumps(registry.to_dict(), indent=2))
        elif format == "prometheus":
            click.echo(registry.to_prometheus_format())
        else:
            metrics = registry.to_dict()
            if not metrics:
                click.echo("No metrics registered.")
                return

            click.echo("Metrics:")
            click.echo("")
            for name, metric in metrics.items():
                metric_type = metric.get("type", "unknown")
                click.echo(f"  {name} ({metric_type}):")

                if metric_type in ["counter", "gauge"]:
                    click.echo(f"    Value: {metric.get('value', 0)}")
                elif metric_type == "histogram":
                    stats = metric.get("statistics", {})
                    click.echo(f"    Count: {stats.get('count', 0)}")
                    click.echo(f"    Avg: {stats.get('avg', 0):.3f}")
                    click.echo(f"    P50: {stats.get('p50', 0):.3f}")
                    click.echo(f"    P95: {stats.get('p95', 0):.3f}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
