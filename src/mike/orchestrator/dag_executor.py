"""DAG-based execution engine for Mike.

Executes ExecutionPlans respecting dependencies, enabling parallel branches,
result passing between nodes, conditional execution, and cancellation propagation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .context_engine import ContextEngine
from .planner import ExecutionPlan, PlanNode

logger = logging.getLogger(__name__)


@dataclass
class NodeResult:
    node_id: str
    agent_type: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0


@dataclass
class DAGResult:
    plan: ExecutionPlan
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    total_duration_ms: int = 0
    status: str = "pending"


def _evaluate_condition(condition: Optional[str], predecessor_results: Dict[str, NodeResult]) -> bool:
    if condition is None:
        return True

    if condition == "if_suggestions_exist":
        for nr in predecessor_results.values():
            if nr.result and nr.result.get("suggestions"):
                return True
        return False

    if condition == "if_needed=True":
        for nr in predecessor_results.values():
            if nr.result and nr.result.get("action_needed") is False:
                return False
        return True

    return True


class DAGExecutor:
    """Executes an ExecutionPlan as a DAG using Kahn's algorithm.

    Supports parallel branch execution via asyncio.gather, result passing
    between dependent nodes, conditional execution, and cancellation
    propagation when predecessors fail.
    """

    def __init__(self, agent_registry: Any, context_engine: ContextEngine, max_workers: int = 4):
        self._registry = agent_registry
        self._context_engine = context_engine
        self._max_workers = max_workers

    async def execute(
        self,
        plan: ExecutionPlan,
        session_id: str,
        shared_context: Optional[Dict[str, Any]] = None,
    ) -> DAGResult:
        start_time = time.monotonic()
        dag_result = DAGResult(plan=plan)
        node_map = {n.id: n for n in plan.nodes}

        # Build in-degree map and successors map
        in_degree: Dict[str, int] = {n.id: 0 for n in plan.nodes}
        successors: Dict[str, List[str]] = {n.id: [] for n in plan.nodes}
        for node in plan.nodes:
            for dep in node.depends_on:
                in_degree[node.id] += 1
                successors[dep].append(node.id)

        failed_nodes: Set[str] = set()
        ready = [nid for nid, deg in in_degree.items() if deg == 0]

        while ready:
            tasks = []
            for nid in ready:
                node = node_map[nid]

                # Cancel if any predecessor failed
                if any(dep in failed_nodes for dep in node.depends_on):
                    dag_result.node_results[nid] = NodeResult(
                        node_id=nid,
                        agent_type=node.agent_type,
                        status="cancelled",
                        error="Predecessor failed",
                    )
                    failed_nodes.add(nid)
                    continue

                # Check condition
                pred_results = {
                    dep: dag_result.node_results[dep]
                    for dep in node.depends_on
                    if dep in dag_result.node_results
                }
                if not _evaluate_condition(node.condition, pred_results):
                    dag_result.node_results[nid] = NodeResult(
                        node_id=nid,
                        agent_type=node.agent_type,
                        status="skipped",
                    )
                    continue

                tasks.append(self._execute_node(node, session_id, dag_result, shared_context))

            if tasks:
                await asyncio.gather(*tasks)

            # Track failures from this round
            for nid in ready:
                if nid in dag_result.node_results and dag_result.node_results[nid].status == "failed":
                    failed_nodes.add(nid)

            # Compute next ready set
            next_ready = []
            for nid in ready:
                for succ in successors.get(nid, []):
                    in_degree[succ] -= 1
                    if in_degree[succ] == 0:
                        next_ready.append(succ)
            ready = next_ready

        # Compute overall status
        statuses = {nr.status for nr in dag_result.node_results.values()}
        if all(s in ("success", "skipped") for s in statuses):
            dag_result.status = "success"
        elif "success" in statuses:
            dag_result.status = "partial"
        else:
            dag_result.status = "failed"

        dag_result.total_duration_ms = int((time.monotonic() - start_time) * 1000)
        return dag_result

    async def _execute_node(
        self,
        node: PlanNode,
        session_id: str,
        dag_result: DAGResult,
        shared_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        start = time.monotonic()

        # Build shared context with predecessor results
        pred_shared = dict(shared_context or {})
        for dep_id in node.depends_on:
            if dep_id in dag_result.node_results:
                dep_result = dag_result.node_results[dep_id]
                if dep_result.result:
                    pred_shared[f"result_{dep_id}"] = dep_result.result

        try:
            agent = self._registry.get(node.agent_type)
            if agent is None:
                raise ValueError(f"No agent registered for type: {node.agent_type}")

            context_bundle = self._context_engine.build(
                query=node.description,
                agent_type=node.agent_type,
                session_id=session_id,
                shared_context=pred_shared,
            )

            agent_context = context_bundle.to_dict()
            agent_context.update(node.parameters)
            result = agent.execute(node.description, agent_context)

            duration = int((time.monotonic() - start) * 1000)
            dag_result.node_results[node.id] = NodeResult(
                node_id=node.id,
                agent_type=node.agent_type,
                status="success",
                result=result,
                duration_ms=duration,
            )

        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            logger.error(f"Node {node.id} failed: {e}")
            dag_result.node_results[node.id] = NodeResult(
                node_id=node.id,
                agent_type=node.agent_type,
                status="failed",
                error=str(e),
                duration_ms=duration,
            )

    def execute_sync(
        self,
        plan: ExecutionPlan,
        session_id: str,
        shared_context: Optional[Dict[str, Any]] = None,
    ) -> DAGResult:
        """Synchronous wrapper for execute().

        Uses asyncio.run() when no event loop is running, or a
        ThreadPoolExecutor when called from within an existing loop.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    self.execute(plan, session_id, shared_context),
                )
                return future.result()
        else:
            return asyncio.run(self.execute(plan, session_id, shared_context))
