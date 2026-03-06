# Mike Testing Infrastructure

Comprehensive testing infrastructure with 90%+ code coverage target.

## Test Structure

```
tests/
├── conftest.py                      # Pytest configuration and fixtures
├── __init__.py
├── unit/                            # Unit tests
│   ├── test_scanner.py              # File scanner tests
│   ├── test_parser.py               # AST parser tests
│   ├── test_chunker.py              # Code chunker tests
│   ├── test_embeddings.py           # Embedding service tests
│   ├── test_vectorstore.py          # Vector store tests
│   ├── test_graph.py                # Graph builder tests
│   ├── test_cache.py                # Cache module tests
│   ├── test_config.py               # Configuration tests
│   └── test_agents/                 # Agent unit tests
│       ├── test_qa_agent.py
│       ├── test_refactor_agent.py
│       └── test_rebuilder_agent.py
├── integration/                     # Integration tests
│   ├── test_pipeline.py             # Full pipeline tests
│   └── test_agents.py               # Agent integration tests
├── e2e/                             # End-to-end tests
│   └── test_cli.py                  # CLI tests
├── fixtures/                        # Test fixtures
│   ├── sample_repos/                # Sample repositories
│   │   ├── python_project/
│   │   ├── javascript_project/
│   │   ├── mixed_project/
│   │   └── monorepo/
│   └── sample_repo/
├── utils/                           # Test utilities
│   ├── assertions.py                # Custom assertions
│   ├── factories.py                 # Object factories
│   └── helpers.py                   # Test helpers
├── cache/                           # Cache tests
├── db/                              # Database tests
├── docs/                            # Documentation tests
├── parser/                          # Parser tests
├── scanner/                         # Scanner tests
└── performance/                     # Performance tests
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run only unit tests
```bash
pytest -m unit
```

### Run only integration tests
```bash
pytest -m integration
```

### Run only E2E tests
```bash
pytest -m e2e
```

### Run tests excluding slow tests
```bash
pytest -m "not slow"
```

### Run with coverage report
```bash
pytest --cov=src/mike --cov-report=html
```

### Run specific test file
```bash
pytest tests/unit/test_scanner.py
```

### Run specific test
```bash
pytest tests/unit/test_scanner.py::TestFileScanner::test_scanner_initialization
```

### Run tests in parallel
```bash
pytest -n auto
```

## Test Categories

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Fast execution (< 30 seconds total)
- Located in `tests/unit/`

### Integration Tests
- Test component interactions
- Test full pipeline flows
- May use real (but temporary) resources
- Located in `tests/integration/`

### E2E Tests
- Test complete workflows
- Test CLI commands
- Test user scenarios
- Located in `tests/e2e/`

### Performance Tests
- Benchmark execution times
- Located in `tests/performance/`

## Fixtures

### Session-scoped fixtures
- `test_dir`: Path to tests directory
- `project_root`: Path to project root
- `sample_repos_dir`: Path to sample repositories

### Function-scoped fixtures
- `temp_dir`: Temporary directory
- `temp_repo`: Temporary repository structure
- `temp_db_path`: Temporary database file
- `db_connection`: SQLite connection
- `test_session_id`: Unique test session ID

### Mock fixtures
- `mock_embedding_service`: Mock embedding service
- `mock_llm_client`: Mock LLM client
- `mock_ollama_client`: Mock Ollama client
- `mock_database`: Mock database instance

### Sample code fixtures
- `sample_python_code`: Python code sample
- `sample_javascript_code`: JavaScript code sample
- `sample_go_code`: Go code sample
- `sample_java_code`: Java code sample
- `sample_code_with_issues`: Code with known issues

## Coverage Strategy

### Target: 90%+ code coverage

### Coverage configuration
- Branch coverage enabled
- HTML report in `htmlcov/`
- XML report in `coverage.xml`
- Missing lines shown in terminal

### Excluded from coverage
- Test files
- Conftest.py
- Migration files
- Virtual environment files

## Test Utilities

### Custom Assertions (`tests/utils/assertions.py`)
- `assert_valid_file_info()`: Validate file info structure
- `assert_valid_chunk()`: Validate chunk structure
- `assert_valid_ast_result()`: Validate AST result
- `assert_valid_embedding()`: Validate embedding vector
- `assert_valid_graph_stats()`: Validate graph statistics
- `assert_valid_qa_response()`: Validate Q&A response
- `assert_valid_code_smell()`: Validate code smell
- `assert_no_secrets_in_code()`: Check for secrets in code

### Factories (`tests/utils/factories.py`)
- `FileInfoFactory`: Create file info objects
- `ChunkFactory`: Create code chunks
- `ASTNodeFactory`: Create AST node metadata
- `GraphEdgeFactory`: Create graph edges
- `SessionFactory`: Create session data
- `CodeSmellFactory`: Create code smell objects
- `MockLLMFactory`: Create mock LLM responses

### Helpers (`tests/utils/helpers.py`)
- `create_test_file()`: Create test file with content
- `create_sample_python_project()`: Create Python project structure
- `create_sample_javascript_project()`: Create JS project structure
- `create_mixed_language_project()`: Create mixed project
- `create_monorepo_structure()`: Create monorepo structure
- `count_lines_of_code()`: Count LOC by extension
- `generate_large_codebase()`: Generate large codebase for performance tests

## Best Practices

### Test Naming
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Descriptive names that explain what is being tested

### Test Structure
- Arrange-Act-Assert pattern
- One assertion per test (ideally)
- Clear comments explaining the test
- Use fixtures for common setup

### Mocking
- Mock external services (LLMs, databases)
- Use `unittest.mock` for mocking
- Use fixtures for reusable mocks

### Test Data
- Use fixtures for test data
- Keep test data in `tests/fixtures/`
- Generate test data with factories
- Avoid hardcoded values

### Performance
- Mark slow tests with `@pytest.mark.slow`
- Use `pytest-benchmark` for benchmarks
- Run tests in parallel with `pytest-xdist`

## Continuous Integration

Tests are designed to run in CI/CD pipeline:
1. Unit tests (fast)
2. Integration tests (medium)
3. E2E tests (slower)
4. Coverage check
5. Performance benchmarks

## Troubleshooting

### Tests failing
1. Check if dependencies are installed: `pip install -e ".[dev]"`
2. Check if test database is accessible
3. Run with verbose output: `pytest -v --tb=long`

### Coverage not meeting target
1. Check coverage report: `pytest --cov=src/mike --cov-report=html`
2. Identify uncovered code
3. Add tests for uncovered code
4. Update exclusions if appropriate

### Slow tests
1. Identify slow tests: `pytest --durations=10`
2. Mark slow tests with `@pytest.mark.slow`
3. Skip slow tests during development: `pytest -m "not slow"`
