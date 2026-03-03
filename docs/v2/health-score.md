# Architecture Health Score

The Architecture Health Score provides a comprehensive assessment of your codebase's architectural quality across multiple dimensions. This feature helps you identify problem areas, track improvements over time, and maintain high-quality code architecture.

## Overview

The Health Score Engine analyzes your codebase and calculates scores across seven key dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Coupling** | 20% | Inter-module dependencies and fan-in/fan-out metrics |
| **Cohesion** | 15% | Class/method relatedness using LCOM (Lack of Cohesion of Methods) |
| **Circular Dependencies** | 20% | Detection of circular import/reference chains |
| **Complexity** | 25% | Cyclomatic complexity analysis |
| **Layer Violations** | 5% | Architectural layer rule enforcement |
| **Unused Exports** | 5% | Dead code detection |
| **Test Coverage** | 10% | Test coverage integration (optional) |

## How Scoring Works

### Overall Score Calculation

The overall health score is a weighted average of all dimension scores:

```
Overall Score = Σ(Dimension Score × Weight) / Σ(Weights)
```

Each dimension score ranges from 0-100, with 100 being optimal.

### Score Categories

| Range | Category | Description |
|-------|----------|-------------|
| 90-100 | Excellent | Architecture is in great shape |
| 75-89 | Good | Minor improvements possible |
| 60-74 | Fair | Needs attention in some areas |
| 40-59 | Poor | Significant issues present |
| 0-39 | Critical | Major refactoring needed |

## Dimension Explanations

### Coupling Score

Measures how interconnected your modules are.

**Calculation:**
- Fan-in: Number of files depending on a given file
- Fan-out: Number of files a given file depends on
- Lower coupling = higher score

**Recommendations:**
- Keep average coupling ≤ 5 for perfect scores
- Files with >10 dependencies are flagged as high coupling

```python
from mike.health.calculator import HealthScoreCalculator
from mike.graph.builder import DependencyGraphBuilder
from mike.parser.parser import ASTParser

# Build dependency graph
graph_builder = DependencyGraphBuilder()
parser = ASTParser()

calculator = HealthScoreCalculator(graph_builder, parser)
coupling_score = calculator.calculate_coupling_score()

print(f"Coupling Score: {coupling_score.score}")
print(f"Avg Fan-in: {coupling_score.details['avg_fan_in']}")
print(f"Avg Fan-out: {coupling_score.details['avg_fan_out']}")
```

### Cohesion Score

Measures how well the methods of a class work together.

**LCOM (Lack of Cohesion of Methods):**
- LCOM = 0: Perfect cohesion (all methods use all instance variables)
- LCOM = 1: No cohesion (methods are unrelated)

**Calculation:**
- Analyzes instance variable usage across methods
- Classes with 0-1 methods have perfect cohesion by definition
- Larger classes with many methods score lower

```python
cohesion_score = calculator.calculate_cohesion_score(file_contents)

print(f"Cohesion Score: {cohesion_score.score}")
print(f"Avg LCOM: {cohesion_score.details['avg_lcom']}")
```

### Circular Dependencies

Detects circular import chains that make code hard to maintain.

**Scoring:**
- 0 cycles: 100 points
- 1-3 cycles: 80 points
- 4-10 cycles: 60 points
- 10+ cycles: 40 points or less

```python
circular_score = calculator.calculate_circular_deps_score()

print(f"Cycles found: {circular_score.details['cycle_count']}")
for cycle in circular_score.details['cycles']:
    print(f"  Cycle: {' -> '.join(cycle['files'])}")
```

### Complexity Score

Measures cyclomatic complexity of your codebase.

**Cyclomatic Complexity Levels:**
- 0-5: Excellent (100 points)
- 5-10: Good (80 points)
- 10-20: Fair (60 points)
- 20+: Poor (decreasing score)

**Factors counted:**
- if/else statements
- for/while loops
- case statements
- Logical operators (&&, ||)

```python
complexity_score = calculator.calculate_complexity_score(file_contents)

print(f"Complexity Score: {complexity_score.score}")
print(f"Avg Complexity: {complexity_score.details['avg_complexity']}")
print(f"Max Complexity: {complexity_score.details['max_complexity']}")
```

### Layer Violations

Validates architectural layering rules (requires configuration).

**Configuration:**
```python
layer_config = {
    "domain": ["models/", "entities/"],
    "service": ["services/", "business/"],
    "api": ["api/", "routes/", "controllers/"],
}

calculator = HealthScoreCalculator(graph_builder, parser, layer_config)
layer_score = calculator.calculate_layer_violations_score()
```

**Rules:**
- Lower layers should NOT depend on higher layers
- Domain layer should be independent
- API layer can depend on service layer
- Service layer can depend on domain layer

### Unused Exports

Detects exported functions/classes that are never imported.

**Scoring:**
- Ratio of unused exports to total exports
- Score = 100 - (unused_ratio × 100)

```python
unused_score = calculator.calculate_unused_exports_score(file_contents)

print(f"Unused Exports: {unused_score.details['unused_count']}")
print(f"Total Exports: {unused_score.details['total_exports']}")
for unused in unused_score.details['unused_exports']:
    print(f"  - {unused['file']}::{unused['export']}")
```

## Interpreting Results

### Full Health Report

```python
from mike.health.calculator import HealthScoreCalculator

# Calculate full score
score = calculator.calculate_overall_score(file_contents)

# Overall assessment
print(f"Overall Health Score: {score.overall_score}/100")
print(f"Category: {score.category.title()}")

# Breakdown by dimension
print("\nDimension Breakdown:")
for ds in score.dimension_scores:
    print(f"  {ds.dimension.value}: {ds.score}/100 (weight: {ds.weight})")
    if ds.issues:
        for issue in ds.issues[:3]:  # Show top 3 issues
            print(f"    ⚠️ {issue}")

# Recommendations
print("\nRecommendations:")
for rec in score.recommendations:
    print(f"  • {rec}")
```

### Exporting Results

```python
import json

# Export to JSON
score_dict = score.to_dict()
with open("health_report.json", "w") as f:
    json.dump(score_dict, f, indent=2)

# Export to Markdown
with open("health_report.md", "w") as f:
    f.write(f"# Architecture Health Report\n\n")
    f.write(f"**Overall Score:** {score.overall_score}/100\n\n")
    f.write(f"**Category:** {score.category}\n\n")
    f.write("## Dimensions\n\n")
    for ds in score.dimension_scores:
        f.write(f"### {ds.dimension.value}\n\n")
        f.write(f"- Score: {ds.score}/100\n")
        f.write(f"- Weight: {ds.weight}\n")
        if ds.issues:
            f.write("- Issues:\n")
            for issue in ds.issues:
                f.write(f"  - {issue}\n")
        f.write("\n")
```

## Configuration Options

### Custom Thresholds

```python
from mike.health.models import ScoreThresholds

# Custom thresholds
thresholds = ScoreThresholds(
    excellent=85.0,  # Lower bar for excellent
    good=70.0,
    fair=55.0,
    poor=35.0,
)

category = thresholds.get_category(82.0)  # Returns "excellent"
```

### Custom Weights

```python
from mike.health.models import ScoreDimension, DIMENSION_WEIGHTS

# Modify weights
DIMENSION_WEIGHTS[ScoreDimension.COMPLEXITY] = 0.30  # Increase complexity weight
DIMENSION_WEIGHTS[ScoreDimension.COUPLING] = 0.15     # Decrease coupling weight
```

### Test Coverage Integration

```python
# Include test coverage in scoring
coverage_score = 85.0  # From your test suite

score = calculator.calculate_overall_score(
    file_contents=file_contents,
    include_test_coverage=True,
    test_coverage_score=coverage_score
)
```

## Best Practices

### 1. Regular Monitoring

Run health scores periodically (e.g., weekly or per release):

```bash
# Add to CI/CD pipeline
mike health <session-id> --output health_report.json
```

### 2. Set Baselines

Establish baseline scores and track trends:

```python
# Store baseline
baseline = score.overall_score

# Compare future scores
if current_score < baseline - 10:
    print("⚠️ Health score degraded significantly!")
```

### 3. Focus on High-Weight Dimensions

Prioritize improvements in high-weight dimensions:
- Complexity (25%) - Most impactful
- Coupling (20%) - Second most impactful
- Circular Dependencies (20%) - Third most impactful

### 4. Layer Configuration

Always configure layer rules for layered architectures:

```python
layer_config = {
    "infrastructure": ["db/", "cache/", "queue/"],
    "application": ["services/", "use_cases/"],
    "domain": ["entities/", "value_objects/"],
    "interface": ["api/", "cli/", "web/"],
}
```

### 5. CI Integration

Example GitHub Action:

```yaml
name: Architecture Health Check

on: [push, pull_request]

jobs:
  health:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Health Check
        run: |
          pip install mike
          mike scan . --session-name "Health Check"
          mike health $SESSION_ID --min-score 70
```

## Troubleshooting

### Low Cohesion Scores

If cohesion scores are unexpectedly low:
1. Check if classes have too many methods (>15)
2. Verify instance variable usage is being analyzed
3. Consider splitting large classes

### High Complexity

For high complexity scores:
1. Extract complex conditionals into named functions
2. Use early returns to reduce nesting
3. Apply the Strategy pattern for complex branching

### Circular Dependencies

To resolve circular dependencies:
1. Use dependency injection
2. Extract common code into a third module
3. Apply the Interface Segregation Principle
4. Consider event-driven architecture

## UI Integration

The web interface provides a visual health score dashboard:

```
┌─────────────────────────────────────────────────────────┐
│ Architecture Health Score                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Overall: 78/100 (Good)                                 │
│  ████████████████████████████████████░░░░░░░░░░░       │
│                                                         │
│  Dimensions:                                            │
│  • Complexity:      85 ████████████████████████████    │
│  • Coupling:        72 ████████████████████████░░░░    │
│  • Cohesion:        68 ██████████████████████░░░░░░    │
│  • Circular Deps:   90 ████████████████████████████    │
│  • Layer Violations: 95 ████████████████████████████   │
│  • Unused Exports:  88 ████████████████████████████    │
│                                                         │
│  Recommendations (3):                                   │
│  1. Reduce dependencies in utils.py                     │
│  2. Split LargeClass into smaller components            │
│  3. Remove unused exports from api.py                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## API Reference

### HealthScoreCalculator

```python
class HealthScoreCalculator:
    def __init__(
        self,
        graph_builder: DependencyGraphBuilder,
        parser: ASTParser,
        layer_config: Optional[Dict[str, List[str]]] = None,
    )
    
    def calculate_overall_score(
        self,
        file_contents: Optional[Dict[str, str]] = None,
        include_test_coverage: bool = False,
        test_coverage_score: Optional[float] = None,
    ) -> ArchitectureScore
```

### ArchitectureScore

```python
@dataclass
class ArchitectureScore:
    overall_score: float
    dimension_scores: List[DimensionScore]
    category: str
    recommendations: List[str]
    
    def get_dimension_score(
        self, dimension: ScoreDimension
    ) -> Optional[DimensionScore]
    
    def to_dict(self) -> Dict
```
