# Git Intelligence

The Git Intelligence module provides deep analytics on your repository's history, helping you identify code hotspots, track technical debt, and understand contributor patterns. This feature leverages git metadata to provide insights that static analysis alone cannot offer.

## Overview

Git Intelligence analyzes:

- **Code Churn** - How much code changes over time
- **Hotspots** - Files that change frequently with high bug correlation
- **Bug-Prone Files** - Files with frequent bug fixes
- **Author Statistics** - Contributor metrics and patterns
- **Rework Rate** - How much code is modified vs. new code

## Metrics Definitions

### Code Churn

**Definition:** Total lines added + deleted in recent commits.

Churn represents the activity level in your codebase. High churn areas often indicate:
- Active development
- Instability
- Technical debt accumulation

**Calculation:**
```python
churn = Σ(added_lines + deleted_lines) across commits
```

**Example:**
```python
from mike.git import GitAnalyzer

analyzer = GitAnalyzer("/path/to/repo")
churn = analyzer.calculate_churn(limit=100)  # Last 100 commits

print(f"Total churn: {churn} lines")
```

### Hotspot Score

**Definition:** Files with high change frequency AND high bug correlation.

**Formula:**
```
Hotspot Score = (commits × bug_fixes) / contributors
```

Higher scores indicate files that are both frequently modified and problematic.

**Example:**
```python
hotspots = analyzer.identify_hotspots(limit=100, top_n=10)

for hotspot in hotspots:
    print(f"{hotspot.path}: {hotspot.score:.2f}")
    print(f"  Commits: {hotspot.commit_count}")
    print(f"  Bug fixes: {hotspot.bug_fixes}")
    print(f"  Contributors: {hotspot.contributor_count}")
```

### Rework Rate

**Definition:** Ratio of deleted lines to total changes.

**Formula:**
```
Rework Rate = deleted_lines / (added_lines + deleted_lines)
```

- **Low rework (0-0.3):** Mostly new feature development
- **Medium rework (0.3-0.6):** Mix of new and refactored code
- **High rework (0.6+):** Heavy refactoring or bug fixing

**Example:**
```python
# Overall repository rework rate
repo_rework = analyzer.calculate_rework_rate(limit=100)

# Per-file rework rate
file_rework = analyzer.calculate_rework_rate(
    file_path="src/complex_module.py",
    limit=100
)

print(f"Repository rework rate: {repo_rework:.2%}")
print(f"File rework rate: {file_rework:.2%}")
```

### Contributor Metrics

**Definitions:**

| Metric | Description |
|--------|-------------|
| **Commit Count** | Total commits by author |
| **Files Touched** | Unique files modified |
| **Lines Added** | Total lines contributed |
| **Lines Deleted** | Total lines removed |
| **Bug Fix Commits** | Commits with bug fix keywords |
| **Avg Commit Size** | Average lines changed per commit |
| **Rework Rate** | Personal rework percentage |

**Example:**
```python
authors = analyzer.get_author_stats(limit=1000)

for author in authors[:5]:  # Top 5 contributors
    print(f"{author.name} <{author.email}>")
    print(f"  Commits: {author.commit_count}")
    print(f"  Files touched: {author.files_touched}")
    print(f"  Avg commit size: {author.avg_commit_size:.1f} lines")
    print(f"  Rework rate: {author.rework_rate:.1%}")
```

## Hotspot Calculation

### Identifying Hotspots

Hotspots are calculated based on:

1. **Commit Frequency** - How often the file changes
2. **Bug Correlation** - How often bug fixes touch the file
3. **Contributor Count** - How many people work on the file

**Algorithm:**
```python
for file in all_files:
    score = (commit_count × bug_fixes) / contributor_count
    
    # Additional factors
    score += (lines_added + lines_deleted) / 1000  # Size factor
    score += recency_bonus if last_commit < 30_days
    
    hotspots.append(FileHotspot(file, score))
```

### Interpreting Hotspot Results

```python
hotspots = analyzer.identify_hotspots(top_n=20)

for i, hotspot in enumerate(hotspots, 1):
    # Categorize by score
    if hotspot.score > 50:
        priority = "🔴 CRITICAL"
    elif hotspot.score > 20:
        priority = "🟠 HIGH"
    elif hotspot.score > 10:
        priority = "🟡 MEDIUM"
    else:
        priority = "🟢 LOW"
    
    print(f"{priority} {i}. {hotspot.path}")
    print(f"   Score: {hotspot.score:.2f}")
    print(f"   {hotspot.commit_count} commits, "
          f"{hotspot.bug_fixes} bug fixes, "
          f"{hotspot.contributor_count} contributors")
    
    if hotspot.top_contributors:
        print(f"   Top contributor: {hotspot.top_contributors[0]}")
```

## Using Results for Refactoring

### 1. Prioritize Hotspots

Focus refactoring efforts on high-scoring hotspots:

```python
# Get critical hotspots
critical_hotspots = [
    h for h in analyzer.identify_hotspots(top_n=50)
    if h.score > 50
]

print(f"Found {len(critical_hotspots)} critical hotspots")
for hotspot in critical_hotspots:
    print(f"  - {hotspot.path}: Score {hotspot.score:.2f}")
```

### 2. Analyze Patterns

Identify patterns in problematic files:

```python
# Group by directory
from collections import defaultdict
hotspots_by_dir = defaultdict(list)

for hotspot in analyzer.identify_hotspots(top_n=50):
    dir_name = hotspot.path.split('/')[0]
    hotspots_by_dir[dir_name].append(hotspot)

# Find problematic directories
for dir_name, hotspots in hotspots_by_dir.items():
    avg_score = sum(h.score for h in hotspots) / len(hotspots)
    if avg_score > 20:
        print(f"⚠️ {dir_name}/ has high hotspot density")
        print(f"   Average score: {avg_score:.2f}")
        print(f"   Hotspots: {len(hotspots)}")
```

### 3. Monitor Improvements

Track if refactoring efforts are working:

```python
import json
from datetime import datetime

def save_hotspots_snapshot(analyzer, filename="hotspots_history.json"):
    """Save current hotspot scores for trend analysis."""
    hotspots = analyzer.identify_hotspots(top_n=50)
    
    snapshot = {
        "date": datetime.now().isoformat(),
        "hotspots": [
            {
                "path": h.path,
                "score": h.score,
                "commits": h.commit_count,
                "bug_fixes": h.bug_fixes,
            }
            for h in hotspots
        ]
    }
    
    # Load existing history
    try:
        with open(filename) as f:
            history = json.load(f)
    except FileNotFoundError:
        history = []
    
    history.append(snapshot)
    
    with open(filename, "w") as f:
        json.dump(history, f, indent=2)

def compare_hotspots(filename="hotspots_history.json"):
    """Compare current hotspots with previous snapshot."""
    with open(filename) as f:
        history = json.load(f)
    
    if len(history) < 2:
        print("Need at least 2 snapshots to compare")
        return
    
    current = history[-1]
    previous = history[-2]
    
    prev_scores = {h["path"]: h["score"] for h in previous["hotspots"]}
    
    print("Hotspot Changes:")
    for hotspot in current["hotspots"][:10]:
        path = hotspot["path"]
        current_score = hotspot["score"]
        prev_score = prev_scores.get(path, 0)
        
        change = current_score - prev_score
        if change > 0:
            trend = "📈"
        elif change < 0:
            trend = "📉"
        else:
            trend = "➡️"
        
        print(f"  {trend} {path}: {prev_score:.2f} → {current_score:.2f}")
```

### 4. Identify Knowledge Silos

Find files with single contributors (bus factor risk):

```python
hotspots = analyzer.identify_hotspots(top_n=50)

silo_risks = [
    h for h in hotspots
    if h.contributor_count == 1 and h.commit_count > 5
]

print("Knowledge Silos (Single Contributor):")
for hotspot in silo_risks:
    print(f"  ⚠️ {hotspot.path}")
    print(f"     Author: {hotspot.top_contributors[0]}")
    print(f"     Commits: {hotspot.commit_count}")
```

### 5. Detect Code Ownership

Understand who knows which parts of the codebase:

```python
authors = analyzer.get_author_stats(limit=1000)

# Map authors to their primary files
ownership = {}
for author in authors:
    for file_path in author.top_files[:5]:  # Top 5 files per author
        if file_path not in ownership:
            ownership[file_path] = []
        ownership[file_path].append({
            "name": author.name,
            "commits": author.file_commits.get(file_path, 0)
        })

# Find files with unclear ownership
unclear = {
    path: owners for path, owners in ownership.items()
    if len(owners) > 3  # Many contributors
}

print("Files with Unclear Ownership:")
for path, owners in unclear.items():
    print(f"  {path}: {len(owners)} contributors")
```

## Refactoring Workflow

### Step 1: Identify Candidates

```python
analyzer = GitAnalyzer("/path/to/repo")

# Get comprehensive metrics
metrics = analyzer.analyze_repository(since_days=90)
hotspots = analyzer.identify_hotspots(top_n=20)
bug_prone = analyzer.detect_bug_prone_files(min_bug_fixes=3)

print(f"Repository Metrics (Last 90 days):")
print(f"  Total commits: {metrics.total_commits}")
print(f"  Bug fix commits: {metrics.bug_fix_commits}")
print(f"  Average commits/day: {metrics.avg_commits_per_day:.2f}")
print(f"  Top contributors: {', '.join(metrics.top_contributors[:3])}")
```

### Step 2: Analyze Specific Hotspot

```python
# Pick top hotspot
top_hotspot = hotspots[0]

# Get detailed file history
file_path = top_hotspot.path

# Calculate rework rate for this file
file_rework = analyzer.calculate_rework_rate(file_path=file_path)

# Get author statistics for this file
file_authors = [
    a for a in analyzer.get_author_stats()
    if file_path in a.top_files
]

print(f"\nDetailed Analysis: {file_path}")
print(f"  Hotspot score: {top_hotspot.score:.2f}")
print(f"  Rework rate: {file_rework:.1%}")
print(f"  Primary authors:")
for author in file_authors[:3]:
    file_commits = author.file_commits.get(file_path, 0)
    print(f"    - {author.name}: {file_commits} commits")
```

### Step 3: Plan Refactoring

Based on analysis, decide on refactoring strategy:

```python
def get_refactoring_recommendation(hotspot, rework_rate):
    """Generate refactoring recommendation based on metrics."""
    recommendations = []
    
    if hotspot.score > 50:
        recommendations.append(
            "🔴 CRITICAL: Immediate refactoring recommended"
        )
    elif hotspot.score > 20:
        recommendations.append(
            "🟠 HIGH: Schedule refactoring in next sprint"
        )
    
    if rework_rate > 0.6:
        recommendations.append(
            "High rework rate suggests design issues - "
            "consider architectural changes"
        )
    elif rework_rate > 0.4:
        recommendations.append(
            "Medium rework - add tests before refactoring"
        )
    
    if hotspot.contributor_count == 1:
        recommendations.append(
            "Single contributor risk - pair program for knowledge transfer"
        )
    
    if hotspot.bug_fixes > hotspot.commit_count * 0.3:
        recommendations.append(
            "High bug correlation - focus on unit tests"
        )
    
    return recommendations

for hotspot in hotspots[:5]:
    rework = analyzer.calculate_rework_rate(file_path=hotspot.path)
    recs = get_refactoring_recommendation(hotspot, rework)
    
    print(f"\n{hotspot.path}")
    for rec in recs:
        print(f"  {rec}")
```

### Step 4: Monitor Post-Refactoring

```python
# After refactoring, monitor if hotspot score decreases
def monitor_refactoring(analyzer, file_path, weeks=4):
    """Monitor file metrics over time."""
    import time
    
    initial_metrics = None
    
    for week in range(weeks):
        # Wait a week (in practice, run this periodically)
        print(f"\nWeek {week + 1}:")
        
        # Get current metrics
        current_hotspots = analyzer.identify_hotspots(top_n=100)
        current_hotspot = next(
            (h for h in current_hotspots if h.path == file_path),
            None
        )
        
        if current_hotspot:
            print(f"  Score: {current_hotspot.score:.2f}")
            print(f"  Commits: {current_hotspot.commit_count}")
            print(f"  Bug fixes: {current_hotspot.bug_fixes}")
            
            if initial_metrics is None:
                initial_metrics = current_hotspot
            else:
                score_change = (
                    current_hotspot.score - initial_metrics.score
                ) / initial_metrics.score * 100
                print(f"  Score change: {score_change:+.1f}%")
        else:
            print("  File no longer in top hotspots! ✓")
        
        if week < weeks - 1:
            time.sleep(7 * 24 * 3600)  # Wait a week
```

## Visualization

### Generate Charts

```python
import matplotlib.pyplot as plt

def plot_hotspots(hotspots, output_path="hotspots.png"):
    """Create hotspot visualization."""
    paths = [h.path.split('/')[-1] for h in hotspots[:10]]
    scores = [h.score for h in hotspots[:10]]
    
    plt.figure(figsize=(12, 6))
    bars = plt.barh(paths, scores, color='coral')
    
    # Color bars by severity
    for bar, score in zip(bars, scores):
        if score > 50:
            bar.set_color('red')
        elif score > 20:
            bar.set_color('orange')
        else:
            bar.set_color('yellow')
    
    plt.xlabel('Hotspot Score')
    plt.title('Top 10 Code Hotspots')
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"Chart saved to {output_path}")

# Generate chart
plot_hotspots(hotspots)
```

### Export Metrics

```python
def export_metrics_to_json(analyzer, output_path="git_metrics.json"):
    """Export all metrics to JSON."""
    metrics = analyzer.analyze_repository()
    hotspots = analyzer.identify_hotspots(top_n=50)
    authors = analyzer.get_author_stats()[:10]
    
    data = {
        "repository_metrics": {
            "total_commits": metrics.total_commits,
            "total_files": metrics.total_files,
            "total_lines": metrics.total_lines,
            "churn": metrics.churn,
            "bug_fix_commits": metrics.bug_fix_commits,
            "avg_commits_per_day": metrics.avg_commits_per_day,
        },
        "hotspots": [
            {
                "path": h.path,
                "score": h.score,
                "commit_count": h.commit_count,
                "bug_fixes": h.bug_fixes,
                "contributor_count": h.contributor_count,
            }
            for h in hotspots
        ],
        "top_contributors": [
            {
                "name": a.name,
                "email": a.email,
                "commits": a.commit_count,
                "files_touched": a.files_touched,
            }
            for a in authors
        ],
    }
    
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Metrics exported to {output_path}")
```

## CLI Integration

### Git Analyze Command

```bash
# Analyze repository
mike git analyze . --since-days 90

# Show hotspots
mike git hotspots . --top 20

# Export metrics
mike git export . --format json --output metrics.json
```

## Best Practices

### 1. Regular Monitoring

Schedule weekly hotspot analysis:

```bash
# Add to CI/CD or cron
mike git analyze . --since-days 7 --output weekly_report.json
```

### 2. Set Thresholds

Define acceptable hotspot scores for your team:

```python
HOTSPOT_THRESHOLDS = {
    "critical": 50,  # Must refactor immediately
    "high": 20,      # Schedule next sprint
    "medium": 10,    # Monitor
}

def check_thresholds(analyzer):
    hotspots = analyzer.identify_hotspots(top_n=50)
    
    critical = [h for h in hotspots if h.score > HOTSPOT_THRESHOLDS["critical"]]
    high = [h for h in hotspots if HOTSPOT_THRESHOLDS["high"] < h.score <= 50]
    
    if critical:
        print(f"🚨 {len(critical)} critical hotspots found!")
        for h in critical:
            print(f"   - {h.path}: {h.score:.2f}")
    
    return len(critical) == 0  # Return False if critical issues found
```

### 3. Team Integration

Share hotspot reports in team meetings:

```markdown
# Weekly Hotspot Report

## New Hotspots This Week
- src/complex_module.py (Score: 45.2 ↑ from 38.1)

## Resolved Hotspots
- ✓ src/old_module.py (No longer in top 50)

## Action Items
- [ ] Review src/complex_module.py (@team-lead)
- [ ] Add tests to src/buggy_file.py (@developer-a)
```

### 4. Pre-Commit Hooks

Warn about changes to hotspot files:

```python
#!/usr/bin/env python
# .git/hooks/pre-commit

import subprocess
from mike.git import GitAnalyzer

analyzer = GitAnalyzer(".")
hotspots = analyzer.identify_hotspots(top_n=20)
hotspot_paths = {h.path for h in hotspots}

# Get staged files
staged = subprocess.check_output(
    ["git", "diff", "--cached", "--name-only"]
).decode().splitlines()

# Check if any staged file is a hotspot
for file_path in staged:
    if file_path in hotspot_paths:
        hotspot = next(h for h in hotspots if h.path == file_path)
        print(f"⚠️  Warning: {file_path} is a hotspot (score: {hotspot.score:.2f})")
        print("    Consider reviewing with a colleague.")
```

## Troubleshooting

### Large Repositories

For repositories with 10k+ commits:

```python
# Limit commit analysis
metrics = analyzer.analyze_repository(limit=1000)  # Last 1000 commits
hotspots = analyzer.identify_hotspots(limit=500)    # Last 500 commits
```

### Shallow Clones

Git Intelligence requires full git history:

```bash
# Unshallow if needed
git fetch --unshallow

# Or clone with full history
git clone --no-single-branch <repo-url>
```

### Performance

If analysis is slow:

1. **Reduce commit limit** - Analyze fewer commits
2. **Filter by date** - Use `since_days` parameter
3. **Skip binary files** - They're excluded by default
4. **Parallel processing** - Analyze multiple repos concurrently
