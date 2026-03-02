#!/usr/bin/env python3
"""
Demo script for testing M8 - Rebuilder Agent implementation.

This script demonstrates the Rebuilder Agent's capabilities without requiring Ollama.
For full LLM-based generation, ensure Ollama is running with a suitable model.

Usage:
    python demo_rebuilder.py --help
    python demo_rebuilder.py scaffold --output ./test_project
    python demo_rebuilder.py full --source ./sample_repo --output ./generated
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from architectai.agents.rebuilder_agent import (
    RebuilderAgent,
    ArchitectureTemplate,
    ArchitecturePattern,
    BuildPlan,
)


def create_sample_template() -> ArchitectureTemplate:
    """Create a sample architecture template for testing."""
    return ArchitectureTemplate(
        source_repo="/sample/api",
        languages=["python"],
        frameworks=["fastapi"],
        patterns=[
            ArchitecturePattern(
                pattern_type="api",
                confidence=0.9,
                components=["routers", "models", "services"],
                description="REST API with layered architecture",
                files_involved=["main.py", "routers/api.py"],
                relationships={"routers": ["models"], "services": ["models"]},
            )
        ],
        directory_structure={
            "root_files": ["README.md", "pyproject.toml"],
            "source_dirs": ["src"],
            "test_dirs": ["tests"],
        },
        dependencies={
            "production": ["fastapi", "uvicorn", "pydantic"],
            "development": ["pytest", "black", "mypy"],
        },
        file_templates={},
        config_patterns={},
        entry_points=["src/main.py"],
        tests_structure={"test_dirs": ["tests"], "test_frameworks": ["pytest"]},
        documentation_structure={"doc_files": ["README.md"]},
    )


def demo_scaffold(args):
    """Demo project scaffolding."""
    print("=" * 70)
    print("🚀 M8 Rebuilder Agent - Scaffolding Demo")
    print("=" * 70)

    # Initialize agent
    agent = RebuilderAgent(
        model_name="mock-model",  # Won't be used for scaffolding
        output_dir=args.output,
    )

    # Create sample template
    print("\n1️⃣ Creating architecture template...")
    template = create_sample_template()
    print(f"   ✓ Template created for {template.languages[0]} project")

    # Generate build plan
    print("\n2️⃣ Generating build plan...")
    plan = agent.generate_build_plan(
        template=template,
        project_name=args.project_name,
        description="A sample FastAPI web application",
        constraints=args.constraints,
    )
    print(f"   ✓ Build plan generated: {plan.plan_id}")
    print(f"   ✓ Files to generate: {len(plan.files)}")
    print(f"   ✓ Constraints: {plan.constraints}")

    if plan.ambiguities:
        print(f"   ⚠️  Ambiguities detected: {len(plan.ambiguities)}")
        for amb in plan.ambiguities:
            print(f"      - {amb}")

    # Export plan for review
    print("\n3️⃣ Exporting build plan...")
    plan_path = agent.export_plan(plan)
    print(f"   ✓ Plan exported to: {plan_path}")

    # Scaffold project
    print("\n4️⃣ Scaffolding project...")
    project_path = agent.scaffold_project(plan)
    print(f"   ✓ Project scaffolded at: {project_path}")

    # List generated files
    print("\n5️⃣ Generated structure:")
    project_dir = Path(project_path)
    for item in sorted(project_dir.rglob("*")):
        if item.is_file():
            rel_path = item.relative_to(project_dir)
            print(f"   📄 {rel_path}")
        elif item.is_dir() and not any(p.startswith(".") for p in item.parts):
            rel_path = item.relative_to(project_dir)
            print(f"   📁 {rel_path}/")

    # Run self-review
    print("\n6️⃣ Running self-review...")
    review = agent.self_review(plan, project_path)
    print(f"   ✓ Coverage: {review.coverage_score:.0%}")
    print(f"   ✓ Issues found: {len(review.issues)}")
    print(f"   ✓ Suggestions: {len(review.suggestions)}")

    if review.suggestions:
        print("\n   Suggestions:")
        for suggestion in review.suggestions:
            print(f"      💡 {suggestion}")

    print("\n" + "=" * 70)
    print("✅ Demo completed successfully!")
    print(f"📁 Project location: {project_path}")
    print("=" * 70)


def demo_full_workflow(args):
    """Demo full workflow with constraints."""
    print("=" * 70)
    print("🚀 M8 Rebuilder Agent - Full Workflow Demo")
    print("=" * 70)
    print("\n⚠️  Note: This demo requires Ollama to be running.")
    print("   If Ollama is not available, code generation will fail.")
    print("   Run: ollama serve")
    print()

    if not args.source:
        print("❌ Error: --source is required for full workflow")
        print("   Example: python demo_rebuilder.py full --source ./my_project")
        return

    # Initialize agent
    agent = RebuilderAgent(
        model_name=args.model,
        output_dir=args.output,
    )

    print(f"📁 Source codebase: {args.source}")
    print(f"📁 Output directory: {args.output}")
    print(f"🤖 Model: {args.model}")
    print(f"🔒 Constraints: {args.constraints}")
    print()

    try:
        # Step 1: Extract architecture
        print("1️⃣ Extracting architecture template...")
        template = agent.extract_architecture_template(args.source)
        print(f"   ✓ Detected languages: {', '.join(template.languages)}")
        print(f"   ✓ Detected frameworks: {', '.join(template.frameworks)}")
        print(f"   ✓ Detected patterns: {[p.pattern_type for p in template.patterns]}")

        # Step 2: Generate build plan
        print("\n2️⃣ Generating build plan...")
        plan = agent.generate_build_plan(
            template=template,
            project_name=args.project_name,
            description="Generated project based on analyzed architecture",
            constraints=args.constraints,
        )
        print(f"   ✓ Build plan: {plan.plan_id}")
        print(
            f"   ✓ Target: {plan.target_language} ({plan.target_framework or 'generic'})"
        )
        print(f"   ✓ Files: {len(plan.files)}")

        # Show some files
        print("\n   Sample files to generate:")
        for file_spec in plan.files[:5]:
            print(f"      - {file_spec.path}")
        if len(plan.files) > 5:
            print(f"      ... and {len(plan.files) - 5} more")

        # Step 3: Scaffold
        print("\n3️⃣ Scaffolding project...")
        project_path = agent.scaffold_project(plan)
        print(f"   ✓ Scaffolded: {project_path}")

        # Step 4: Generate code (requires Ollama)
        print("\n4️⃣ Generating code (requires Ollama)...")
        print("   ⏳ This may take a while depending on the model...")
        try:
            generated_files = agent.write_code(
                plan=plan,
                project_path=project_path,
                template=template,
                use_iterative=args.iterative,
            )
            print(f"   ✓ Generated {len(generated_files)} files")

            # Show sample
            if generated_files:
                print("\n   Sample generated files:")
                for i, (path, content) in enumerate(list(generated_files.items())[:3]):
                    preview = content[:100].replace("\n", " ")
                    print(f"      {path}: {preview}...")

        except Exception as e:
            print(f"   ❌ Code generation failed: {e}")
            print("   💡 Ensure Ollama is running: ollama serve")
            print("   💡 Or install a model: ollama pull gemma3:12b")

        # Step 5: Self-review
        print("\n5️⃣ Running self-review...")
        review = agent.self_review(plan, project_path)
        print(f"   ✓ Coverage: {review.coverage_score:.0%}")
        print(f"   ✓ Issues: {len(review.issues)}")

        print("\n" + "=" * 70)
        print("✅ Full workflow demo completed!")
        print(f"📁 Project location: {project_path}")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="Demo script for M8 Rebuilder Agent")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Scaffold command
    scaffold_parser = subparsers.add_parser(
        "scaffold",
        help="Demo project scaffolding (no Ollama required)",
    )
    scaffold_parser.add_argument(
        "--output",
        default="./generated_projects",
        help="Output directory for generated project",
    )
    scaffold_parser.add_argument(
        "--project-name",
        default="demo-project",
        help="Name of the generated project",
    )
    scaffold_parser.add_argument(
        "--constraints",
        nargs="+",
        default=["auth", "redis"],
        help="Constraints to apply (e.g., auth multi-tenant redis)",
    )
    scaffold_parser.set_defaults(func=demo_scaffold)

    # Full command
    full_parser = subparsers.add_parser(
        "full",
        help="Full workflow demo (requires Ollama)",
    )
    full_parser.add_argument(
        "--source",
        required=True,
        help="Path to source codebase to analyze",
    )
    full_parser.add_argument(
        "--output",
        default="./generated_projects",
        help="Output directory for generated project",
    )
    full_parser.add_argument(
        "--project-name",
        default="generated-project",
        help="Name of the generated project",
    )
    full_parser.add_argument(
        "--model",
        default="gemma3:12b",
        help="Ollama model to use",
    )
    full_parser.add_argument(
        "--constraints",
        nargs="+",
        default=[],
        help="Constraints to apply",
    )
    full_parser.add_argument(
        "--iterative",
        action="store_true",
        help="Use iterative generation with testing",
    )
    full_parser.set_defaults(func=demo_full_workflow)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
