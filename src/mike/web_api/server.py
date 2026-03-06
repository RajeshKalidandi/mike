"""FastAPI server with health checks and metrics endpoints."""

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse

from mike.logging_config import get_logger
from mike.monitoring.prometheus_metrics import get_metrics
from mike.monitoring.middleware import setup_middleware

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Mike API",
        description="Local AI Software Architect API",
        version="2.0.0",
        docs_url="/docs" if os.getenv("MIKE_ENV") != "production" else None,
    )

    # Setup middleware
    setup_middleware(app)

    return app


# Create the FastAPI app
app = create_app()
metrics = get_metrics()


def get_db_path() -> Optional[Path]:
    """Get the database path."""
    db_path = os.getenv("MIKE_DB_PATH")
    if db_path:
        return Path(db_path)
    return Path.home() / ".mike" / "mike.db"


def check_database_connection() -> bool:
    """Check if database is accessible."""
    try:
        db_path = get_db_path()
        if not db_path or not db_path.exists():
            return False

        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def check_disk_space() -> Dict[str, Any]:
    """Check available disk space."""
    try:
        import shutil

        path = Path.home()
        stat = shutil.disk_usage(path)

        return {
            "total": stat.total,
            "used": stat.used,
            "free": stat.free,
            "percent_used": (stat.used / stat.total) * 100,
        }
    except Exception as e:
        logger.error(f"Disk space check failed: {e}")
        return {"error": str(e)}


def check_memory() -> Dict[str, Any]:
    """Check system memory."""
    try:
        import psutil

        mem = psutil.virtual_memory()

        return {
            "total": mem.total,
            "available": mem.available,
            "percent": mem.percent,
            "used": mem.used,
        }
    except ImportError:
        return {"error": "psutil not installed"}
    except Exception as e:
        logger.error(f"Memory check failed: {e}")
        return {"error": str(e)}


@app.get("/health", response_class=PlainTextResponse)
async def health_check():
    """Liveness probe - basic health check.

    Returns 200 OK if the service is running.
    """
    return "OK"


@app.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness probe - check if service is ready to handle requests.

    Checks:
    - Database connectivity
    - Disk space availability
    - Memory availability

    Returns 200 if ready, 503 if not ready.
    """
    checks = {
        "database": check_database_connection(),
        "disk": check_disk_space(),
        "memory": check_memory(),
    }

    # Determine overall readiness
    is_ready = checks["database"]

    # Check disk space (fail if less than 100MB free)
    if isinstance(checks["disk"], dict) and "free" in checks["disk"]:
        if checks["disk"]["free"] < 100 * 1024 * 1024:  # 100MB
            is_ready = False
            checks["disk_space_critical"] = True

    # Check memory (warn if > 90% used)
    if isinstance(checks["memory"], dict) and "percent" in checks["memory"]:
        if checks["memory"]["percent"] > 90:
            checks["memory_critical"] = True

    status_code = (
        status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    response = {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }

    if not is_ready:
        raise HTTPException(
            status_code=status_code,
            detail=response,
        )

    return response


@app.get("/health/metrics", response_class=PlainTextResponse)
async def metrics_endpoint():
    """Prometheus metrics endpoint.

    Returns all metrics in Prometheus exposition format.
    """
    return metrics.to_prometheus_format()


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics_alias():
    """Alias for /health/metrics for Prometheus compatibility."""
    return await metrics_endpoint()


@app.get("/health/status")
async def detailed_health_status() -> Dict[str, Any]:
    """Detailed health status with all system information.

    Returns comprehensive health information including:
    - Service status
    - Database status
    - System resources
    - Current metrics snapshot
    """
    # Update system metrics
    try:
        import psutil

        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(Path.home())
        cpu_percent = psutil.cpu_percent(interval=0.1)

        metrics.update_system_metrics(
            memory_bytes=mem.used,
            cpu_percent=cpu_percent,
            disk_bytes=disk.used,
        )
    except Exception as e:
        logger.warning(f"Could not update system metrics: {e}")

    return {
        "service": {
            "status": "healthy",
            "version": "2.0.0",
            "uptime_seconds": None,  # Would need to track start time
        },
        "database": {
            "connected": check_database_connection(),
            "path": str(get_db_path()) if get_db_path() else None,
        },
        "system": {
            "disk": check_disk_space(),
            "memory": check_memory(),
        },
        "metrics": {
            "active_sessions": metrics.sessions_active.get_value(),
            "total_sessions": metrics.sessions_created.get_value(),
            "health_score": metrics.health_score.get_value(),
            "total_vulnerabilities": metrics.vulnerabilities_found.get_value(),
            "cache_hit_rate": metrics.get_cache_hit_rate(),
        },
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }


# WebSocket endpoint for real-time metrics
@app.websocket("/ws/metrics")
async def websocket_metrics(websocket):
    """WebSocket endpoint for real-time metrics streaming."""
    import asyncio
    import json

    await websocket.accept()

    try:
        while True:
            # Send current metrics
            data = {
                "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                "metrics": {
                    "active_sessions": metrics.sessions_active.get_value(),
                    "health_score": metrics.health_score.get_value(),
                    "cache_hit_rate": metrics.get_cache_hit_rate(),
                },
            }
            await websocket.send_text(json.dumps(data))

            # Wait before next update
            await asyncio.sleep(5)
    except Exception as e:
        logger.warning(f"WebSocket connection closed: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MIKE_API_PORT", "8000"))
    host = os.getenv("MIKE_API_HOST", "127.0.0.1")

    uvicorn.run(app, host=host, port=port)
