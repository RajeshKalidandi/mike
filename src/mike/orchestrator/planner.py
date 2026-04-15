# src/mike/orchestrator/planner.py
"""Progressive Planning Architecture for Mike.

Three-tier planning system:
- RulePlanner: direct intent-to-agent mapping for simple queries
- TemplatePlanner: parametric workflow templates for known multi-step patterns
- LLMPlanner: constrained LLM composition for novel queries
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import networkx as nx

from .model_provider import ModelProvider

logger = logging.getLogger(__name__)

ALLOWED_AGENTS = {"qa", "docs", "refactor", "rebuild"}
MAX_LLM_PLAN_NODES = 4


class Complexity(str, Enum):
    SIMPLE = "simple"
    MULTI_STEP = "multi_step"
    OPEN_ENDED = "open_ended"


@dataclass
class IntentResult:
    intent: str
    complexity: Complexity
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanNode:
    id: str
    agent_type: str
    description: str
    depends_on: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None


@dataclass
class ExecutionPlan:
    nodes: List[PlanNode]
    reasoning: str
    planner_type: str
    estimated_duration: Optional[str] = None

    def node_ids(self) -> List[str]:
        return [n.id for n in self.nodes]

    def is_valid_dag(self) -> bool:
        ids = set(self.node_ids())
        for node in self.nodes:
            for dep in node.depends_on:
                if dep not in ids:
                    return False
        g = nx.DiGraph()
        for node in self.nodes:
            g.add_node(node.id)
            for dep in node.depends_on:
                g.add_edge(dep, node.id)
        return nx.is_directed_acyclic_graph(g)


_KEYWORD_RULES = [
    (["document", "readme", "architecture doc", "api reference", "generate docs", "create documentation"], "generate_docs", Complexity.SIMPLE),
    (["refactor", "improve", "code smell", "clean up", "optimize", "restructure", "simplify"], "refactor", Complexity.SIMPLE),
    (["scaffold", "generate project", "create app", "new project", "template", "boilerplate", "rebuild"], "rebuild_project", Complexity.MULTI_STEP),
    (["explain", "how does", "what does", "where is", "find"], "explain_code", Complexity.SIMPLE),
    (["compare", "difference between", "vs"], "compare", Complexity.SIMPLE),
    (["fix", "bug", "error", "broken"], "fix_bug", Complexity.MULTI_STEP),
    (["review", "audit", "assess", "analyze architecture", "health"], "architecture_review", Complexity.MULTI_STEP),
    (["full doc", "all documentation", "complete docs"], "full_documentation", Complexity.MULTI_STEP),
]


def _keyword_classify(query: str) -> IntentResult:
    q = query.lower()
    for keywords, intent, complexity in _KEYWORD_RULES:
        if any(kw in q for kw in keywords):
            return IntentResult(intent=intent, complexity=complexity, confidence=0.6, parameters={})
    return IntentResult(intent="general_qa", complexity=Complexity.SIMPLE, confidence=0.4, parameters={})


_INTENT_PROMPT = """Classify the following user query about a codebase.

Query: "{query}"

Respond with ONLY a JSON object:
{{
  "intent": "<one of: explain_code, find_code, architecture_review, refactor, generate_docs, full_documentation, rebuild_project, fix_bug, compare, general_qa>",
  "complexity": "<one of: simple, multi_step, open_ended>",
  "confidence": <float 0.0-1.0>,
  "parameters": {{<extracted entities like file names, function names, concepts>}}
}}"""


class IntentClassifier:
    def __init__(self, model_provider: ModelProvider):
        self._provider = model_provider

    def classify(self, query: str) -> IntentResult:
        try:
            raw = self._provider.generate_json(
                _INTENT_PROMPT.format(query=query),
                system="You are a query classifier. Return only valid JSON.",
            )
            if not raw or "intent" not in raw:
                return _keyword_classify(query)

            complexity_str = raw.get("complexity", "simple")
            try:
                complexity = Complexity(complexity_str)
            except ValueError:
                complexity = Complexity.SIMPLE

            return IntentResult(
                intent=raw["intent"],
                complexity=complexity,
                confidence=float(raw.get("confidence", 0.7)),
                parameters=raw.get("parameters", {}),
            )
        except Exception as e:
            logger.warning(f"LLM intent classification failed, using keyword fallback: {e}")
            return _keyword_classify(query)


_INTENT_TO_AGENT = {
    "explain_code": "qa",
    "find_code": "qa",
    "general_qa": "qa",
    "compare": "qa",
    "generate_docs": "docs",
    "refactor": "refactor",
    "rebuild_project": "rebuild",
    "fix_bug": "refactor",
}


class RulePlanner:
    def plan(self, intent: IntentResult) -> ExecutionPlan:
        agent_type = _INTENT_TO_AGENT.get(intent.intent, "qa")
        node = PlanNode(
            id="main",
            agent_type=agent_type,
            description=f"Handle {intent.intent} query",
            depends_on=[],
            parameters=intent.parameters.copy(),
        )
        return ExecutionPlan(
            nodes=[node],
            reasoning=f"Simple {intent.intent} query routed to {agent_type} agent",
            planner_type="rule",
        )


def _build_templates() -> Dict[str, List[PlanNode]]:
    return {
        "architecture_review": [
            PlanNode(id="scan", agent_type="qa", description="Analyze codebase structure",
                     depends_on=[], parameters={"focus": "architecture"}),
            PlanNode(id="health", agent_type="refactor", description="Assess architecture health",
                     depends_on=["scan"], parameters={"focus": "health_scoring"}),
            PlanNode(id="suggest", agent_type="refactor", description="Generate improvement suggestions",
                     depends_on=["health"], parameters={"focus": "suggestions"}),
        ],
        "full_documentation": [
            PlanNode(id="scan", agent_type="qa", description="Survey codebase",
                     depends_on=[], parameters={}),
            PlanNode(id="readme", agent_type="docs", description="Generate README",
                     depends_on=["scan"], parameters={"doc_type": "readme"}),
            PlanNode(id="arch", agent_type="docs", description="Generate architecture docs",
                     depends_on=["scan"], parameters={"doc_type": "architecture"}),
            PlanNode(id="api", agent_type="docs", description="Generate API reference",
                     depends_on=["scan"], parameters={"doc_type": "api"}),
        ],
        "refactor_with_review": [
            PlanNode(id="analyze", agent_type="refactor", description="Analyze code smells",
                     depends_on=[], parameters={}),
            PlanNode(id="suggest", agent_type="refactor", description="Generate refactoring plan",
                     depends_on=["analyze"], parameters={}),
            PlanNode(id="verify", agent_type="qa", description="Verify suggestions are safe",
                     depends_on=["suggest"], parameters={"focus": "safety_check"},
                     condition="if_suggestions_exist"),
        ],
        "rebuild_project": [
            PlanNode(id="analyze", agent_type="qa", description="Understand existing architecture",
                     depends_on=[], parameters={"depth": "comprehensive"}),
            PlanNode(id="plan", agent_type="rebuild", description="Generate build plan",
                     depends_on=["analyze"], parameters={}),
            PlanNode(id="scaffold", agent_type="rebuild", description="Scaffold project",
                     depends_on=["plan"], parameters={}),
        ],
        "fix_bug": [
            PlanNode(id="locate", agent_type="qa", description="Locate bug in codebase",
                     depends_on=[], parameters={"focus": "bug_location"}),
            PlanNode(id="fix", agent_type="refactor", description="Suggest fix",
                     depends_on=["locate"], parameters={}),
        ],
    }


class TemplatePlanner:
    def __init__(self):
        self._templates = _build_templates()

    def plan(self, intent: IntentResult) -> ExecutionPlan:
        template = self._templates.get(intent.intent)
        if template is None:
            agent_type = _INTENT_TO_AGENT.get(intent.intent, "qa")
            return ExecutionPlan(
                nodes=[PlanNode(id="main", agent_type=agent_type, description=f"Handle {intent.intent}",
                                depends_on=[], parameters=intent.parameters.copy())],
                reasoning=f"No template for {intent.intent}, using single agent",
                planner_type="template",
            )

        nodes = []
        for node in template:
            new_node = PlanNode(
                id=node.id,
                agent_type=node.agent_type,
                description=node.description,
                depends_on=list(node.depends_on),
                parameters={**node.parameters, **intent.parameters},
                condition=node.condition,
            )
            nodes.append(new_node)

        return ExecutionPlan(
            nodes=nodes,
            reasoning=f"Using {intent.intent} template with {len(nodes)} steps",
            planner_type="template",
        )


_LLM_PLANNING_PROMPT = """You are a planning engine. Given a user query about a codebase,
create an execution plan using ONLY these available agents:

Available agents:
- qa: Answer questions, explain code, find code locations
- docs: Generate documentation (README, architecture, API reference)
- refactor: Analyze code quality, suggest improvements, detect smells
- rebuild: Scaffold new projects, generate code, create boilerplate

Constraints:
- Maximum {max_nodes} steps
- Must form a valid DAG (no cycles)
- Each step must specify depends_on as a list of step IDs

Query: "{query}"

Respond with ONLY a JSON object:
{{
  "reasoning": "<why this plan>",
  "steps": [
    {{"id": "<unique_id>", "agent": "<agent_type>", "description": "<what>", "depends_on": [], "parameters": {{}}}}
  ]
}}"""


class LLMPlanner:
    def __init__(self, model_provider: ModelProvider):
        self._provider = model_provider

    def plan(self, intent: IntentResult) -> ExecutionPlan:
        try:
            raw = self._provider.generate_json(
                _LLM_PLANNING_PROMPT.format(query=intent.intent, max_nodes=MAX_LLM_PLAN_NODES),
                system="You are a planning engine. Return only valid JSON.",
            )
            if not raw or "steps" not in raw:
                return self._fallback(intent, "LLM returned no steps")

            nodes = self._parse_steps(raw["steps"])
            plan = ExecutionPlan(
                nodes=nodes,
                reasoning=raw.get("reasoning", "LLM-generated plan"),
                planner_type="llm",
            )

            if not self._validate(plan):
                return self._fallback(intent, "LLM plan failed validation")

            return plan

        except Exception as e:
            logger.warning(f"LLM planning failed: {e}")
            return self._fallback(intent, str(e))

    def _parse_steps(self, steps: List[Dict[str, Any]]) -> List[PlanNode]:
        nodes = []
        for step in steps:
            nodes.append(PlanNode(
                id=step.get("id", f"step_{len(nodes)}"),
                agent_type=step.get("agent", "qa"),
                description=step.get("description", ""),
                depends_on=step.get("depends_on", []),
                parameters=step.get("parameters", {}),
            ))
        return nodes

    def _validate(self, plan: ExecutionPlan) -> bool:
        if len(plan.nodes) > MAX_LLM_PLAN_NODES:
            logger.warning(f"LLM plan has {len(plan.nodes)} nodes, max is {MAX_LLM_PLAN_NODES}")
            return False

        for node in plan.nodes:
            if node.agent_type not in ALLOWED_AGENTS:
                logger.warning(f"LLM plan contains invalid agent type: {node.agent_type}")
                return False

        if not plan.is_valid_dag():
            logger.warning("LLM plan is not a valid DAG")
            return False

        return True

    def _fallback(self, intent: IntentResult, reason: str) -> ExecutionPlan:
        logger.info(f"LLM planner falling back: {reason}")
        return ExecutionPlan(
            nodes=[PlanNode(
                id="main", agent_type="qa",
                description=f"Handle query (LLM planning failed: {reason})",
                depends_on=[], parameters=intent.parameters.copy(),
            )],
            reasoning=f"Fallback: {reason}",
            planner_type="llm_fallback",
        )


class StrategyRouter:
    def __init__(self, rule_planner: RulePlanner, template_planner: TemplatePlanner, llm_planner: LLMPlanner):
        self._rule = rule_planner
        self._template = template_planner
        self._llm = llm_planner

    def plan(self, intent: IntentResult) -> ExecutionPlan:
        if intent.complexity == Complexity.SIMPLE:
            return self._rule.plan(intent)
        elif intent.complexity == Complexity.MULTI_STEP:
            return self._template.plan(intent)
        else:
            return self._llm.plan(intent)
