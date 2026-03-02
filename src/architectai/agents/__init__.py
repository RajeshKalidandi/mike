"""Agents module for ArchitectAI.

This module contains AI agents for various tasks:
- Q&A Agent: Answer questions about the codebase
- Documentation Agent: Generate documentation (M3)
- Refactor Agent: Suggest improvements (M5)
- Rebuilder Agent: Generate new code (M6/M8)
"""

from .qa_agent import QAAgent, QueryAnalyzer, QAResponse, QueryIntent, SourceReference
from .refactor_agent import RefactorAgent, RefactorReportGenerator
from .rebuilder_agent import (
    RebuilderAgent,
    RebuilderWorkflow,
    BuildPlan,
    ArchitectureTemplate,
    ArchitecturePattern,
    FileSpec,
    ReviewResult,
    GenerationProgress,
    BuildPlanStatus,
    GenerationPhase,
)
from .scaffolder import ProjectScaffolder, ScaffoldingConfig
from .code_generator import CodeGenerator, GenerationConfig
from .patterns import (
    CodeSmell,
    ASTPatternMatcher,
    DuplicateDetector,
    ComplexityAnalyzer,
    DependencyAnalyzer,
)

__all__ = [
    "QAAgent",
    "QueryAnalyzer",
    "QAResponse",
    "QueryIntent",
    "SourceReference",
    "RefactorAgent",
    "RefactorReportGenerator",
    # Rebuilder Agent
    "RebuilderAgent",
    "RebuilderWorkflow",
    "BuildPlan",
    "ArchitectureTemplate",
    "ArchitecturePattern",
    "FileSpec",
    "ReviewResult",
    "GenerationProgress",
    "BuildPlanStatus",
    "GenerationPhase",
    # Scaffolder
    "ProjectScaffolder",
    "ScaffoldingConfig",
    # Code Generator
    "CodeGenerator",
    "GenerationConfig",
    # Pattern Analysis
    "CodeSmell",
    "ASTPatternMatcher",
    "DuplicateDetector",
    "ComplexityAnalyzer",
    "DependencyAnalyzer",
]
