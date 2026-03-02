"""Unit tests for the AST Parser module."""

import pytest

from architectai.parser.parser import ASTParser
from architectai.parser.languages import normalize_language, is_language_supported


class TestASTParser:
    """Test cases for ASTParser."""

    def test_parser_initialization(self):
        """Test that parser initializes correctly."""
        parser = ASTParser()
        assert parser._parsers == {}

    def test_parse_unsupported_language(self):
        """Test parsing unsupported language returns empty structure."""
        parser = ASTParser()
        result = parser.parse("code", "unsupported_language")

        assert result["functions"] == []
        assert result["classes"] == []
        assert result["imports"] == []
        assert result["language"] == "unsupported_language"

    def test_parse_python_simple_function(self):
        """Test parsing simple Python function."""
        parser = ASTParser()
        code = "def main():\n    pass"

        result = parser.parse(code, "python")

        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "main"
        assert result["functions"][0]["start_line"] == 1
        assert result["functions"][0]["end_line"] == 2

    def test_parse_python_function_with_params(self):
        """Test parsing Python function with parameters."""
        parser = ASTParser()
        code = "def greet(name, age=18):\n    print(f'Hello {name}')"

        result = parser.parse(code, "python")

        assert len(result["functions"]) == 1
        func = result["functions"][0]
        assert func["name"] == "greet"
        assert "name" in func["parameters"]

    def test_parse_python_class(self):
        """Test parsing Python class."""
        parser = ASTParser()
        code = """
class MyClass:
    def __init__(self):
        self.value = 0
    
    def get_value(self):
        return self.value
"""

        result = parser.parse(code, "python")

        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "MyClass"

        # Methods should NOT be extracted as top-level functions
        assert len(result["functions"]) == 0

    def test_parse_python_imports(self):
        """Test parsing Python imports."""
        parser = ASTParser()
        code = """
import os
import sys
from typing import List, Optional
from pathlib import Path
"""

        result = parser.parse(code, "python")

        assert len(result["imports"]) >= 2
        import_names = {imp["name"] for imp in result["imports"]}
        assert "os" in import_names
        assert "sys" in import_names

    def test_parse_javascript_function(self):
        """Test parsing JavaScript function."""
        parser = ASTParser()
        code = """
function greet(name) {
    console.log('Hello, ' + name);
}

const add = (a, b) => a + b;
"""

        result = parser.parse(code, "javascript")

        assert len(result["functions"]) >= 1
        func_names = {f["name"] for f in result["functions"]}
        assert "greet" in func_names
        assert "add" in func_names

    def test_parse_javascript_class(self):
        """Test parsing JavaScript class."""
        parser = ASTParser()
        code = """
class Person {
    constructor(name) {
        this.name = name;
    }
    
    greet() {
        console.log('Hello, I am ' + this.name);
    }
}
"""

        result = parser.parse(code, "javascript")

        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "Person"

    def test_parse_javascript_imports(self):
        """Test parsing JavaScript imports."""
        parser = ASTParser()
        code = """
import React from 'react';
import { useState, useEffect } from 'react';
import * as utils from './utils';
"""

        result = parser.parse(code, "javascript")

        assert len(result["imports"]) >= 1

    def test_parse_go_function(self):
        """Test parsing Go function."""
        parser = ASTParser()
        code = """
package main

func main() {
    println("Hello, World!")
}

func add(a, b int) int {
    return a + b
}
"""

        result = parser.parse(code, "go")

        assert len(result["functions"]) == 2
        func_names = {f["name"] for f in result["functions"]}
        assert "main" in func_names
        assert "add" in func_names

    def test_parse_go_struct(self):
        """Test parsing Go struct."""
        parser = ASTParser()
        code = """
package main

type Person struct {
    Name string
    Age  int
}

type Status int
"""

        result = parser.parse(code, "go")

        # Go structs are treated as classes
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "Person"

    def test_parse_java_class(self):
        """Test parsing Java class."""
        parser = ASTParser()
        code = """
package com.example;

import java.util.List;

public class OrderService {
    private List<Order> orders;
    
    public Order getOrder(String id) {
        return orders.stream()
            .filter(o -> o.getId().equals(id))
            .findFirst()
            .orElse(null);
    }
}
"""

        result = parser.parse(code, "java")

        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "OrderService"

    def test_parse_java_imports(self):
        """Test parsing Java imports."""
        parser = ASTParser()
        code = """
import java.util.List;
import java.util.ArrayList;
import com.example.model.Order;
"""

        result = parser.parse(code, "java")

        assert len(result["imports"]) >= 1

    def test_parse_rust_function(self):
        """Test parsing Rust function."""
        parser = ASTParser()
        code = """
fn main() {
    println!("Hello, World!");
}

fn add(a: i32, b: i32) -> i32 {
    a + b
}
"""

        result = parser.parse(code, "rust")

        assert len(result["functions"]) == 2
        func_names = {f["name"] for f in result["functions"]}
        assert "main" in func_names
        assert "add" in func_names

    def test_parse_rust_struct(self):
        """Test parsing Rust struct."""
        parser = ASTParser()
        code = """
struct Point {
    x: f64,
    y: f64,
}

enum Status {
    Active,
    Inactive,
}
"""

        result = parser.parse(code, "rust")

        assert len(result["classes"]) == 2
        class_names = {c["name"] for c in result["classes"]}
        assert "Point" in class_names
        assert "Status" in class_names

    def test_parser_caching(self):
        """Test that parsers are cached."""
        parser = ASTParser()

        # First parse creates parser
        parser.parse("def a(): pass", "python")
        assert "python" in parser._parsers

        # Second parse uses cached parser
        first_parser = parser._parsers["python"]
        parser.parse("def b(): pass", "python")
        assert parser._parsers["python"] is first_parser

    def test_parse_empty_code(self):
        """Test parsing empty code."""
        parser = ASTParser()
        result = parser.parse("", "python")

        assert result["functions"] == []
        assert result["classes"] == []
        assert result["imports"] == []

    def test_parse_multiline_functions(self):
        """Test that line numbers are correct for multiline functions."""
        parser = ASTParser()
        code = """def top():
    pass

def middle():
    x = 1
    return x

def bottom():
    pass
"""

        result = parser.parse(code, "python")

        assert len(result["functions"]) == 3

        # Find function by name and check line numbers
        top_func = next(f for f in result["functions"] if f["name"] == "top")
        middle_func = next(f for f in result["functions"] if f["name"] == "middle")
        bottom_func = next(f for f in result["functions"] if f["name"] == "bottom")

        assert top_func["start_line"] == 1
        assert middle_func["start_line"] == 4
        assert bottom_func["start_line"] == 8


class TestLanguageHelpers:
    """Test cases for language helper functions."""

    def test_normalize_language_python(self):
        """Test normalizing Python language names."""
        assert normalize_language("Python") == "python"
        assert normalize_language("python") == "python"
        assert normalize_language("PYTHON") == "python"
        assert normalize_language("py") == "python"

    def test_normalize_language_javascript(self):
        """Test normalizing JavaScript language names."""
        assert normalize_language("JavaScript") == "javascript"
        assert normalize_language("javascript") == "javascript"
        assert normalize_language("js") == "javascript"
        assert normalize_language("JS") == "javascript"

    def test_normalize_language_typescript(self):
        """Test normalizing TypeScript language names."""
        assert normalize_language("TypeScript") == "typescript"
        assert normalize_language("typescript") == "typescript"
        assert normalize_language("ts") == "typescript"

    def test_is_language_supported(self):
        """Test checking if language is supported."""
        assert is_language_supported("python") is True
        assert is_language_supported("javascript") is True
        assert is_language_supported("typescript") is True
        assert is_language_supported("go") is True
        assert is_language_supported("java") is True
        assert is_language_supported("rust") is True
        assert is_language_supported("unsupported") is False
