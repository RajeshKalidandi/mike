import pytest
from pathlib import Path
from architectai.parser.parser import ASTParser


class TestASTParser:
    def test_parse_python_file(self):
        """Test parsing a Python file."""
        parser = ASTParser()

        code = '''
def add(a, b):
    """Add two numbers."""
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
'''

        result = parser.parse(code, "Python")

        assert result is not None
        assert "functions" in result
        assert "classes" in result
        assert "imports" in result

        # Check functions extracted (only top-level functions, not methods)
        func_names = [f["name"] for f in result["functions"]]
        assert "add" in func_names
        # Note: "multiply" is a method inside Calculator class, not a top-level function

        # Check classes extracted
        class_names = [c["name"] for c in result["classes"]]
        assert "Calculator" in class_names

    def test_parse_javascript_file(self):
        """Test parsing a JavaScript file."""
        parser = ASTParser()

        code = """
function greet(name) {
    return `Hello, ${name}!`;
}

class Person {
    constructor(name) {
        this.name = name;
    }
    
    sayHello() {
        console.log(`Hello, I'm ${this.name}`);
    }
}

module.exports = { Person };
"""

        result = parser.parse(code, "JavaScript")

        assert result is not None
        func_names = [f["name"] for f in result["functions"]]
        assert "greet" in func_names

        class_names = [c["name"] for c in result["classes"]]
        assert "Person" in class_names

    def test_extract_imports(self):
        """Test import extraction."""
        parser = ASTParser()

        code = """
import os
import sys
from typing import List
from mymodule import utils, helpers
"""

        result = parser.parse(code, "Python")
        imports = result["imports"]

        import_names = [i["name"] for i in imports]
        assert "os" in import_names
        assert "sys" in import_names
        assert "typing.List" in import_names or "List" in import_names
