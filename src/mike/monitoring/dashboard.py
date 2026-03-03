"""Local dashboard for Mike monitoring."""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class DashboardGenerator:
    """Generate HTML dashboard for monitoring data."""

    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mike Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            border: 1px solid #334155;
        }
        
        h1 {
            font-size: 2rem;
            color: #60a5fa;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #94a3b8;
            font-size: 1rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: #1e293b;
            padding: 24px;
            border-radius: 12px;
            border: 1px solid #334155;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .stat-label {
            font-size: 0.875rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }
        
        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: #60a5fa;
        }
        
        .stat-change {
            font-size: 0.875rem;
            margin-top: 8px;
        }
        
        .positive {
            color: #4ade80;
        }
        
        .negative {
            color: #f87171;
        }
        
        .chart-container {
            background: #1e293b;
            padding: 24px;
            border-radius: 12px;
            border: 1px solid #334155;
            margin-bottom: 20px;
        }
        
        .chart-title {
            font-size: 1.25rem;
            color: #e2e8f0;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid #334155;
        }
        
        .chart-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .table-container {
            background: #1e293b;
            padding: 24px;
            border-radius: 12px;
            border: 1px solid #334155;
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }
        
        th {
            color: #94a3b8;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }
        
        tr:hover {
            background: #334155;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .status-success {
            background: rgba(74, 222, 128, 0.2);
            color: #4ade80;
        }
        
        .status-error {
            background: rgba(248, 113, 113, 0.2);
            color: #f87171;
        }
        
        .status-pending {
            background: rgba(251, 191, 36, 0.2);
            color: #fbbf24;
        }
        
        .refresh-btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.875rem;
            transition: background 0.2s;
        }
        
        .refresh-btn:hover {
            background: #2563eb;
        }
        
        .timestamp {
            color: #64748b;
            font-size: 0.875rem;
            margin-top: 20px;
        }
        
        .metric-bar {
            height: 8px;
            background: #334155;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        
        .metric-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #60a5fa);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Mike Monitoring Dashboard</h1>
            <p class="subtitle">Real-time system performance and telemetry</p>
            <button class="refresh-btn" onclick="location.reload()">Refresh Data</button>
        </header>
        
        <div class="stats-grid">
            {stats_cards}
        </div>
        
        <div class="chart-row">
            <div class="chart-container">
                <h3 class="chart-title">Agent Executions Over Time</h3>
                <canvas id="agentChart"></canvas>
            </div>
            <div class="chart-container">
                <h3 class="chart-title">Success Rate Trend</h3>
                <canvas id="successChart"></canvas>
            </div>
        </div>
        
        <div class="chart-row">
            <div class="chart-container">
                <h3 class="chart-title">Execution Duration Distribution</h3>
                <canvas id="durationChart"></canvas>
            </div>
            <div class="chart-container">
                <h3 class="chart-title">Resource Usage</h3>
                <canvas id="resourceChart"></canvas>
            </div>
        </div>
        
        <div class="table-container">
            <h3 class="chart-title">Recent Agent Executions</h3>
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Agent</th>
                        <th>Duration</th>
                        <th>Status</th>
                        <th>Tokens</th>
                    </tr>
                </thead>
                <tbody>
                    {recent_executions}
                </tbody>
            </table>
        </div>
        
        <div class="table-container">
            <h3 class="chart-title">Agent Performance Comparison</h3>
            <table>
                <thead>
                    <tr>
                        <th>Agent</th>
                        <th>Runs</th>
                        <th>Success Rate</th>
                        <th>Avg Duration</th>
                        <th>Total Tokens</th>
                    </tr>
                </thead>
                <tbody>
                    {agent_comparison}
                </tbody>
            </table>
        </div>
        
        <p class="timestamp">Last updated: {last_updated}</p>
    </div>
    
    <script>
        const chartData = {chart_data};
        
        // Agent executions over time
        new Chart(document.getElementById('agentChart'), {{
            type: 'line',
            data: {{
                labels: chartData.agentExecutions.labels,
                datasets: [{{
                    label: 'Executions',
                    data: chartData.agentExecutions.data,
                    borderColor: '#60a5fa',
                    backgroundColor: 'rgba(96, 165, 250, 0.1)',
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: '#334155' }},
                        ticks: {{ color: '#94a3b8' }}
                    }},
                    x: {{
                        grid: {{ color: '#334155' }},
                        ticks: {{ color: '#94a3b8' }}
                    }}
                }}
            }}
        }});
        
        // Success rate trend
        new Chart(document.getElementById('successChart'), {{
            type: 'line',
            data: {{
                labels: chartData.successRate.labels,
                datasets: [{{
                    label: 'Success Rate (%)',
                    data: chartData.successRate.data,
                    borderColor: '#4ade80',
                    backgroundColor: 'rgba(74, 222, 128, 0.1)',
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        grid: {{ color: '#334155' }},
                        ticks: {{ color: '#94a3b8' }}
                    }},
                    x: {{
                        grid: {{ color: '#334155' }},
                        ticks: {{ color: '#94a3b8' }}
                    }}
                }}
            }}
        }});
        
        // Duration distribution
        new Chart(document.getElementById('durationChart'), {{
            type: 'bar',
            data: {{
                labels: chartData.durationDistribution.labels,
                datasets: [{{
                    label: 'Executions',
                    data: chartData.durationDistribution.data,
                    backgroundColor: '#fbbf24',
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: '#334155' }},
                        ticks: {{ color: '#94a3b8' }}
                    }},
                    x: {{
                        grid: {{ color: '#334155' }},
                        ticks: {{ color: '#94a3b8' }}
                    }}
                }}
            }}
        }});
        
        // Resource usage
        new Chart(document.getElementById('resourceChart'), {{
            type: 'line',
            data: {{
                labels: chartData.resourceUsage.labels,
                datasets: [
                    {{
                        label: 'CPU (%)',
                        data: chartData.resourceUsage.cpu,
                        borderColor: '#f472b6',
                        backgroundColor: 'rgba(244, 114, 182, 0.1)',
                        fill: true,
                        tension: 0.4
                    }},
                    {{
                        label: 'Memory (%)',
                        data: chartData.resourceUsage.memory,
                        borderColor: '#a78bfa',
                        backgroundColor: 'rgba(167, 139, 250, 0.1)',
                        fill: true,
                        tension: 0.4
                    }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: '#334155' }},
                        ticks: {{ color: '#94a3b8' }}
                    }},
                    x: {{
                        grid: {{ color: '#334155' }},
                        ticks: {{ color: '#94a3b8' }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._get_default_db_path()

    def _get_default_db_path(self) -> str:
        """Get default database path."""
        home = Path.home()
        db_dir = home / ".mike"
        return str(db_dir / "telemetry.db")

    def generate_dashboard(self, output_path: str = "dashboard.html") -> str:
        """Generate HTML dashboard file."""
        stats = self._get_stats()
        chart_data = self._get_chart_data()
        recent_executions = self._get_recent_executions()
        agent_comparison = self._get_agent_comparison()

        stats_cards = self._generate_stats_cards(stats)
        recent_executions_html = self._generate_recent_executions_table(
            recent_executions
        )
        agent_comparison_html = self._generate_agent_comparison_table(agent_comparison)

        html = self.HTML_TEMPLATE.format(
            stats_cards=stats_cards,
            chart_data=json.dumps(chart_data),
            recent_executions=recent_executions_html,
            agent_comparison=agent_comparison_html,
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        with open(output_path, "w") as f:
            f.write(html)

        return output_path

    def _get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                COUNT(DISTINCT session_id) as sessions,
                COUNT(*) as events,
                SUM(CASE WHEN event_type = 'agent_complete' THEN 1 ELSE 0 END) as agents,
                SUM(CASE WHEN event_type = 'agent_complete' AND success = 1 THEN 1 ELSE 0 END) as success,
                SUM(CASE WHEN event_type = 'llm_call_complete' THEN 1 ELSE 0 END) as llm_calls
            FROM telemetry_events
        """)

        row = cursor.fetchone()
        conn.close()

        total_agents = row[2] or 0
        success_agents = row[3] or 0

        return {
            "total_sessions": row[0] or 0,
            "total_events": row[1] or 0,
            "total_agent_runs": total_agents,
            "successful_runs": success_agents,
            "success_rate": (success_agents / total_agents * 100)
            if total_agents > 0
            else 0,
            "total_llm_calls": row[4] or 0,
        }

    def _get_chart_data(self) -> Dict[str, Any]:
        """Get data for charts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)

        labels = []
        agent_data = []
        success_data = []

        for i in range(7):
            day_start = start_time + timedelta(days=i)
            day_end = day_start + timedelta(days=1)

            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success
                FROM telemetry_events
                WHERE event_type = 'agent_complete'
                AND timestamp >= ? AND timestamp < ?
            """,
                (day_start.isoformat(), day_end.isoformat()),
            )

            row = cursor.fetchone()
            labels.append(day_start.strftime("%m/%d"))
            agent_data.append(row[0] or 0)
            total = row[0] or 0
            success = row[1] or 0
            success_data.append((success / total * 100) if total > 0 else 0)

        cursor.execute("""
            SELECT 
                CASE 
                    WHEN duration_ms < 1000 THEN '0-1s'
                    WHEN duration_ms < 5000 THEN '1-5s'
                    WHEN duration_ms < 10000 THEN '5-10s'
                    WHEN duration_ms < 30000 THEN '10-30s'
                    WHEN duration_ms < 60000 THEN '30-60s'
                    ELSE '60s+'
                END as bucket,
                COUNT(*) as count
            FROM telemetry_events
            WHERE event_type = 'agent_complete'
            AND duration_ms IS NOT NULL
            GROUP BY bucket
            ORDER BY MIN(duration_ms)
        """)

        duration_labels = []
        duration_data = []
        for row in cursor.fetchall():
            duration_labels.append(row[0])
            duration_data.append(row[1])

        cursor.execute(
            """
            SELECT 
                timestamp,
                cpu_percent,
                memory_percent
            FROM performance_snapshots
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 100
        """,
            (start_time.isoformat(),),
        )

        resource_labels = []
        cpu_data = []
        memory_data = []
        for row in cursor.fetchall():
            resource_labels.append(row[0][11:16])
            cpu_data.append(row[1] or 0)
            memory_data.append(row[2] or 0)

        resource_labels.reverse()
        cpu_data.reverse()
        memory_data.reverse()

        conn.close()

        return {
            "agentExecutions": {"labels": labels, "data": agent_data},
            "successRate": {"labels": labels, "data": success_data},
            "durationDistribution": {"labels": duration_labels, "data": duration_data},
            "resourceUsage": {
                "labels": resource_labels,
                "cpu": cpu_data,
                "memory": memory_data,
            },
        }

    def _get_recent_executions(self) -> List[Dict[str, Any]]:
        """Get recent agent executions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                timestamp,
                agent_name,
                duration_ms,
                success,
                metadata
            FROM telemetry_events
            WHERE event_type = 'agent_complete'
            ORDER BY timestamp DESC
            LIMIT 20
        """)

        executions = []
        for row in cursor.fetchall():
            metadata = json.loads(row[4]) if row[4] else {}
            executions.append(
                {
                    "timestamp": row[0],
                    "agent": row[1] or "unknown",
                    "duration_ms": row[2] or 0,
                    "success": bool(row[3]) if row[3] is not None else None,
                    "tokens": metadata.get("tokens_used", 0),
                }
            )

        conn.close()
        return executions

    def _get_agent_comparison(self) -> List[Dict[str, Any]]:
        """Get agent performance comparison."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                agent_name,
                COUNT(*) as runs,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success,
                AVG(duration_ms) as avg_duration
            FROM telemetry_events
            WHERE event_type = 'agent_complete'
            AND agent_name IS NOT NULL
            GROUP BY agent_name
            ORDER BY runs DESC
        """)

        agents = []
        for row in cursor.fetchall():
            runs = row[1] or 0
            success = row[2] or 0
            agents.append(
                {
                    "name": row[0],
                    "runs": runs,
                    "success_rate": (success / runs * 100) if runs > 0 else 0,
                    "avg_duration": row[3] or 0,
                    "total_tokens": 0,
                }
            )

        conn.close()
        return agents

    def _generate_stats_cards(self, stats: Dict[str, Any]) -> str:
        """Generate HTML for stats cards."""
        cards = [
            {
                "label": "Total Sessions",
                "value": stats["total_sessions"],
                "change": None,
            },
            {
                "label": "Agent Runs",
                "value": stats["total_agent_runs"],
                "change": None,
            },
            {
                "label": "Success Rate",
                "value": f"{stats['success_rate']:.1f}%",
                "change": "positive" if stats["success_rate"] >= 90 else "negative",
            },
            {
                "label": "LLM Calls",
                "value": stats["total_llm_calls"],
                "change": None,
            },
        ]

        html_parts = []
        for card in cards:
            change_html = ""
            if card["change"]:
                change_class = card["change"]
                change_text = "↑ Good" if change_class == "positive" else "↓ Attention"
                change_html = (
                    f'<div class="stat-change {change_class}">{change_text}</div>'
                )

            html_parts.append(f"""
                <div class="stat-card">
                    <div class="stat-label">{card["label"]}</div>
                    <div class="stat-value">{card["value"]}</div>
                    {change_html}
                </div>
            """)

        return "\n".join(html_parts)

    def _generate_recent_executions_table(
        self, executions: List[Dict[str, Any]]
    ) -> str:
        """Generate HTML for recent executions table."""
        rows = []
        for exec in executions:
            status_class = "status-success" if exec["success"] else "status-error"
            status_text = "Success" if exec["success"] else "Failed"
            duration = (
                f"{exec['duration_ms'] / 1000:.2f}s" if exec["duration_ms"] else "-"
            )

            rows.append(f"""
                <tr>
                    <td>{exec["timestamp"][:19]}</td>
                    <td>{exec["agent"]}</td>
                    <td>{duration}</td>
                    <td><span class="status-badge {status_class}">{status_text}</span></td>
                    <td>{exec["tokens"]}</td>
                </tr>
            """)

        return "\n".join(rows)

    def _generate_agent_comparison_table(self, agents: List[Dict[str, Any]]) -> str:
        """Generate HTML for agent comparison table."""
        rows = []
        for agent in agents:
            success_class = "positive" if agent["success_rate"] >= 90 else "negative"
            avg_duration = (
                f"{agent['avg_duration'] / 1000:.2f}s" if agent["avg_duration"] else "-"
            )

            rows.append(f"""
                <tr>
                    <td>{agent["name"]}</td>
                    <td>{agent["runs"]}</td>
                    <td class="{success_class}">{agent["success_rate"]:.1f}%</td>
                    <td>{avg_duration}</td>
                    <td>{agent["total_tokens"]}</td>
                </tr>
            """)

        return "\n".join(rows)

    def serve_dashboard(
        self, port: int = 8080, dashboard_path: str = "dashboard.html"
    ) -> None:
        """Serve dashboard using a simple HTTP server."""
        import http.server
        import socketserver
        import webbrowser
        from threading import Thread

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

        if not os.path.exists(dashboard_path):
            self.generate_dashboard(dashboard_path)

        directory = os.path.dirname(os.path.abspath(dashboard_path))
        os.chdir(directory)

        with socketserver.TCPServer(("", port), Handler) as httpd:
            url = f"http://localhost:{port}/{os.path.basename(dashboard_path)}"
            print(f"Dashboard serving at {url}")
            webbrowser.open(url)
            httpd.serve_forever()
