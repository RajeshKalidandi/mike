"""AST Parser implementation using tree-sitter."""

from typing import Dict, List, Any, Optional
from tree_sitter import Language, Parser, Tree, Node

from .languages import get_language, normalize_language, is_language_supported


class ASTParser:
    """Parser for extracting code structure from source files using tree-sitter."""

    def __init__(self):
        """Initialize parser cache."""
        self._parsers: Dict[str, Parser] = {}

    def _get_parser(self, language: str) -> Optional[Parser]:
        """Get or create a parser for the specified language.

        Args:
            language: The language name.

        Returns:
            A tree-sitter Parser instance, or None if language not supported.
        """
        normalized = normalize_language(language)

        if normalized not in self._parsers:
            lang_obj = get_language(language)
            if lang_obj is None:
                return None

            parser = Parser(lang_obj)
            self._parsers[normalized] = parser

        return self._parsers[normalized]

    def parse(self, code: str, language: str) -> Dict[str, Any]:
        """Parse source code and extract code structure.

        Args:
            code: The source code to parse.
            language: The programming language of the code.

        Returns:
            Dictionary containing extracted code structure with keys:
            - functions: List of function definitions
            - classes: List of class definitions
            - imports: List of imports
            - language: The normalized language name
        """
        if not is_language_supported(language):
            return {
                "functions": [],
                "classes": [],
                "imports": [],
                "language": normalize_language(language),
            }

        parser = self._get_parser(language)
        if parser is None:
            return {
                "functions": [],
                "classes": [],
                "imports": [],
                "language": normalize_language(language),
            }

        # Parse the code
        tree = parser.parse(bytes(code, "utf-8"))
        root = tree.root_node

        # Extract code elements
        normalized_lang = normalize_language(language)

        return {
            "functions": self._extract_functions(root, normalized_lang),
            "classes": self._extract_classes(root, normalized_lang),
            "imports": self._extract_imports(root, normalized_lang),
            "language": normalized_lang,
        }

    def _extract_functions(self, root: Node, language: str) -> List[Dict[str, Any]]:
        """Extract function definitions from the AST.

        Args:
            root: The root node of the AST.
            language: The normalized language name.

        Returns:
            List of function dictionaries with name, parameters, start_line, end_line.
        """
        functions = []

        if language == "python":
            functions = self._extract_python_functions(root)
        elif language in ("javascript", "typescript"):
            functions = self._extract_javascript_functions(root)
        elif language == "go":
            functions = self._extract_go_functions(root)
        elif language == "java":
            functions = self._extract_java_functions(root)
        elif language == "rust":
            functions = self._extract_rust_functions(root)
        elif language in ("c", "cpp"):
            functions = self._extract_c_functions(root)
        elif language == "ruby":
            functions = self._extract_ruby_functions(root)
        elif language == "php":
            functions = self._extract_php_functions(root)

        return functions

    def _extract_python_functions(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Python function definitions."""
        functions = []
        seen = set()  # Track seen (name, start_line) to avoid duplicates

        def traverse(node: Node):
            if node.type == "function_definition":
                # Get function name
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""
                start_line = node.start_point[0] + 1

                # Skip if we've already seen this function at this line
                key = (name, start_line)
                if key in seen:
                    return
                seen.add(key)

                # Get parameters
                params_node = node.child_by_field_name("parameters")
                params = []
                if params_node:
                    for child in params_node.children:
                        if child.type in ("identifier", "typed_parameter"):
                            param_name = child.text.decode("utf-8")
                            params.append(param_name)

                functions.append(
                    {
                        "name": name,
                        "parameters": params,
                        "start_line": start_line,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                # Skip traversing into class definitions to avoid counting methods
                # as top-level functions
                if child.type != "class_definition":
                    traverse(child)

        traverse(root)
        return functions

    def _extract_javascript_functions(self, root: Node) -> List[Dict[str, Any]]:
        """Extract JavaScript/TypeScript function definitions."""
        functions = []

        def traverse(node: Node):
            if node.type in ("function_declaration", "function", "method_definition"):
                name = ""
                if node.type == "function_declaration":
                    name_node = node.child_by_field_name("name")
                    name = name_node.text.decode("utf-8") if name_node else ""
                elif node.type == "method_definition":
                    name_node = node.child_by_field_name("name")
                    name = name_node.text.decode("utf-8") if name_node else ""

                params = []
                params_node = node.child_by_field_name("parameters")
                if params_node:
                    for child in params_node.children:
                        if child.type in (
                            "identifier",
                            "shorthand_property_identifier_pattern",
                        ):
                            params.append(child.text.decode("utf-8"))

                functions.append(
                    {
                        "name": name,
                        "parameters": params,
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            # Handle arrow functions assigned to variables
            if node.type == "variable_declarator":
                name_node = node.child_by_field_name("name")
                value_node = node.child_by_field_name("value")
                if value_node and value_node.type == "arrow_function":
                    name = name_node.text.decode("utf-8") if name_node else ""
                    params = []
                    params_node = value_node.child_by_field_name("parameters")
                    if params_node:
                        for child in params_node.children:
                            if child.type == "identifier":
                                params.append(child.text.decode("utf-8"))

                    functions.append(
                        {
                            "name": name,
                            "parameters": params,
                            "start_line": node.start_point[0] + 1,
                            "end_line": node.end_point[0] + 1,
                        }
                    )

            for child in node.children:
                traverse(child)

        traverse(root)
        return functions

    def _extract_go_functions(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Go function definitions."""
        functions = []

        def traverse(node: Node):
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""

                functions.append(
                    {
                        "name": name,
                        "parameters": [],
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return functions

    def _extract_java_functions(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Java method definitions."""
        functions = []

        def traverse(node: Node):
            if node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""

                functions.append(
                    {
                        "name": name,
                        "parameters": [],
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return functions

    def _extract_rust_functions(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Rust function definitions."""
        functions = []

        def traverse(node: Node):
            if node.type == "function_item":
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""

                functions.append(
                    {
                        "name": name,
                        "parameters": [],
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return functions

    def _extract_c_functions(self, root: Node) -> List[Dict[str, Any]]:
        """Extract C/C++ function definitions."""
        functions = []

        def traverse(node: Node):
            if node.type == "function_definition":
                # Get declarator which contains the name
                declarator = node.child_by_field_name("declarator")
                name = ""
                if declarator:
                    # Navigate to find the identifier
                    if declarator.type == "function_declarator":
                        name_node = declarator.child_by_field_name("declarator")
                        if name_node:
                            name = name_node.text.decode("utf-8")
                    elif declarator.type == "identifier":
                        name = declarator.text.decode("utf-8")

                functions.append(
                    {
                        "name": name,
                        "parameters": [],
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return functions

    def _extract_ruby_functions(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Ruby method definitions."""
        functions = []

        def traverse(node: Node):
            if node.type == "method":
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""

                functions.append(
                    {
                        "name": name,
                        "parameters": [],
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return functions

    def _extract_php_functions(self, root: Node) -> List[Dict[str, Any]]:
        """Extract PHP function definitions."""
        functions = []

        def traverse(node: Node):
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""

                functions.append(
                    {
                        "name": name,
                        "parameters": [],
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return functions

    def _extract_classes(self, root: Node, language: str) -> List[Dict[str, Any]]:
        """Extract class definitions from the AST.

        Args:
            root: The root node of the AST.
            language: The normalized language name.

        Returns:
            List of class dictionaries with name, start_line, end_line.
        """
        classes = []

        if language == "python":
            classes = self._extract_python_classes(root)
        elif language in ("javascript", "typescript"):
            classes = self._extract_javascript_classes(root)
        elif language == "go":
            classes = self._extract_go_classes(root)
        elif language == "java":
            classes = self._extract_java_classes(root)
        elif language == "rust":
            classes = self._extract_rust_classes(root)
        elif language in ("c", "cpp"):
            classes = self._extract_cpp_classes(root)
        elif language == "ruby":
            classes = self._extract_ruby_classes(root)
        elif language == "php":
            classes = self._extract_php_classes(root)

        return classes

    def _extract_python_classes(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Python class definitions with their methods."""
        classes = []

        def traverse(node: Node):
            if node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""

                # Extract methods from class body
                methods = []
                class_body = node.child_by_field_name("body")
                if class_body:
                    for child in class_body.children:
                        if child.type == "function_definition":
                            method_name_node = child.child_by_field_name("name")
                            method_name = (
                                method_name_node.text.decode("utf-8")
                                if method_name_node
                                else ""
                            )
                            methods.append(
                                {
                                    "name": method_name,
                                    "start_line": child.start_point[0] + 1,
                                    "end_line": child.end_point[0] + 1,
                                }
                            )

                classes.append(
                    {
                        "name": name,
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                        "methods": methods,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return classes

    def _extract_javascript_classes(self, root: Node) -> List[Dict[str, Any]]:
        """Extract JavaScript/TypeScript class definitions."""
        classes = []

        def traverse(node: Node):
            if node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""

                classes.append(
                    {
                        "name": name,
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return classes

    def _extract_go_classes(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Go struct/type definitions (treated as classes)."""
        classes = []

        def traverse(node: Node):
            if node.type == "type_declaration":
                # Get the type spec child which contains the actual type definition
                for child in node.children:
                    if child.type == "type_spec":
                        name_node = child.child_by_field_name("name")
                        name = name_node.text.decode("utf-8") if name_node else ""

                        # Check if it's a struct type
                        type_node = child.child_by_field_name("type")
                        if type_node and type_node.type == "struct_type":
                            classes.append(
                                {
                                    "name": name,
                                    "start_line": node.start_point[0] + 1,
                                    "end_line": node.end_point[0] + 1,
                                }
                            )

            for child in node.children:
                traverse(child)

        traverse(root)
        return classes

    def _extract_java_classes(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Java class definitions."""
        classes = []

        def traverse(node: Node):
            if node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""

                classes.append(
                    {
                        "name": name,
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return classes

    def _extract_rust_classes(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Rust struct/enum definitions (treated as classes)."""
        classes = []

        def traverse(node: Node):
            if node.type in ("struct_item", "enum_item"):
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""

                classes.append(
                    {
                        "name": name,
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return classes

    def _extract_cpp_classes(self, root: Node) -> List[Dict[str, Any]]:
        """Extract C++ class definitions."""
        classes = []

        def traverse(node: Node):
            if node.type == "class_specifier":
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""

                classes.append(
                    {
                        "name": name,
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return classes

    def _extract_ruby_classes(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Ruby class definitions."""
        classes = []

        def traverse(node: Node):
            if node.type == "class":
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""

                classes.append(
                    {
                        "name": name,
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return classes

    def _extract_php_classes(self, root: Node) -> List[Dict[str, Any]]:
        """Extract PHP class definitions."""
        classes = []

        def traverse(node: Node):
            if node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else ""

                classes.append(
                    {
                        "name": name,
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1,
                    }
                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return classes

    def _extract_imports(self, root: Node, language: str) -> List[Dict[str, Any]]:
        """Extract import statements from the AST.

        Args:
            root: The root node of the AST.
            language: The normalized language name.

        Returns:
            List of import dictionaries with name and module.
        """
        imports = []

        if language == "python":
            imports = self._extract_python_imports(root)
        elif language in ("javascript", "typescript"):
            imports = self._extract_javascript_imports(root)
        elif language == "go":
            imports = self._extract_go_imports(root)
        elif language == "java":
            imports = self._extract_java_imports(root)
        elif language == "rust":
            imports = self._extract_rust_imports(root)
        elif language in ("c", "cpp"):
            imports = self._extract_c_imports(root)
        elif language == "ruby":
            imports = self._extract_ruby_imports(root)
        elif language == "php":
            imports = self._extract_php_imports(root)

        return imports

    def _extract_python_imports(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Python import statements."""
        imports = []

        def traverse(node: Node):
            if node.type == "import_statement":
                # Simple import: import os, sys
                for child in node.children:
                    if child.type == "dotted_name":
                        name = child.text.decode("utf-8")
                        imports.append(
                            {
                                "name": name,
                                "module": name,
                            }
                        )
                    elif child.type == "identifier":
                        name = child.text.decode("utf-8")
                        imports.append(
                            {
                                "name": name,
                                "module": name,
                            }
                        )

            elif node.type == "import_from_statement":
                # from module import name1, name2
                module_node = None
                names = []

                for i, child in enumerate(node.children):
                    if child.type == "dotted_name":
                        if module_node is None:
                            module_node = child
                        else:
                            names.append(child)
                    elif child.type == "identifier":
                        names.append(child)

                module = module_node.text.decode("utf-8") if module_node else ""

                for name_node in names:
                    name = name_node.text.decode("utf-8")
                    imports.append(
                        {
                            "name": name,
                            "module": f"{module}.{name}" if module else name,
                        }
                    )

            for child in node.children:
                traverse(child)

        traverse(root)
        return imports

    def _extract_javascript_imports(self, root: Node) -> List[Dict[str, Any]]:
        """Extract JavaScript/TypeScript import statements."""
        imports = []

        def traverse(node: Node):
            if node.type == "import_statement":
                # import { name } from 'module'
                # import name from 'module'
                source_node = None

                for child in node.children:
                    if child.type == "string":
                        source_node = child
                        break

                if source_node:
                    module = source_node.text.decode("utf-8").strip("'\"")

                    # Find imported names
                    for child in node.children:
                        if child.type == "import_clause":
                            for subchild in child.children:
                                if subchild.type == "identifier":
                                    name = subchild.text.decode("utf-8")
                                    imports.append(
                                        {
                                            "name": name,
                                            "module": module,
                                        }
                                    )
                                elif subchild.type == "named_imports":
                                    for spec in subchild.children:
                                        if spec.type == "import_specifier":
                                            name_node = spec.child_by_field_name("name")
                                            if name_node:
                                                name = name_node.text.decode("utf-8")
                                                imports.append(
                                                    {
                                                        "name": name,
                                                        "module": module,
                                                    }
                                                )

            for child in node.children:
                traverse(child)

        traverse(root)
        return imports

    def _extract_go_imports(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Go import statements."""
        imports = []

        def traverse(node: Node):
            if node.type == "import_declaration":
                for child in node.children:
                    if child.type == "import_spec":
                        path_node = child.child_by_field_name("path")
                        if path_node:
                            module = path_node.text.decode("utf-8").strip('"')
                            name_node = child.child_by_field_name("name")
                            name = (
                                name_node.text.decode("utf-8") if name_node else module
                            )
                            imports.append(
                                {
                                    "name": name,
                                    "module": module,
                                }
                            )

            for child in node.children:
                traverse(child)

        traverse(root)
        return imports

    def _extract_java_imports(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Java import statements."""
        imports = []

        def traverse(node: Node):
            if node.type == "import_declaration":
                # Get the scoped identifier
                for child in node.children:
                    if child.type in ("scoped_identifier", "identifier"):
                        name = child.text.decode("utf-8")
                        imports.append(
                            {
                                "name": name,
                                "module": name,
                            }
                        )

            for child in node.children:
                traverse(child)

        traverse(root)
        return imports

    def _extract_rust_imports(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Rust use statements."""
        imports = []

        def traverse(node: Node):
            if node.type == "use_declaration":
                # Get the argument which is the use tree
                arg_node = node.child_by_field_name("argument")
                if arg_node:
                    name = arg_node.text.decode("utf-8")
                    imports.append(
                        {
                            "name": name,
                            "module": name,
                        }
                    )

            for child in node.children:
                traverse(child)

        traverse(root)
        return imports

    def _extract_c_imports(self, root: Node) -> List[Dict[str, Any]]:
        """Extract C/C++ include statements."""
        imports = []

        def traverse(node: Node):
            if node.type == "preproc_include":
                for child in node.children:
                    if child.type == "string_literal":
                        name = child.text.decode("utf-8").strip('"<>')
                        imports.append(
                            {
                                "name": name,
                                "module": name,
                            }
                        )

            for child in node.children:
                traverse(child)

        traverse(root)
        return imports

    def _extract_ruby_imports(self, root: Node) -> List[Dict[str, Any]]:
        """Extract Ruby require/load statements."""
        imports = []

        def traverse(node: Node):
            if node.type == "call":
                method_node = node.child_by_field_name("method")
                if method_node:
                    method_name = method_node.text.decode("utf-8")
                    if method_name in ("require", "require_relative", "load"):
                        arg_node = node.child_by_field_name("arguments")
                        if arg_node:
                            for child in arg_node.children:
                                if child.type == "string":
                                    name = child.text.decode("utf-8").strip("'\"")
                                    imports.append(
                                        {
                                            "name": name,
                                            "module": name,
                                        }
                                    )

            for child in node.children:
                traverse(child)

        traverse(root)
        return imports

    def _extract_php_imports(self, root: Node) -> List[Dict[str, Any]]:
        """Extract PHP use/include statements."""
        imports = []

        def traverse(node: Node):
            if node.type in ("use_declaration", "use_statement"):
                for child in node.children:
                    if child.type == "name":
                        name = child.text.decode("utf-8")
                        imports.append(
                            {
                                "name": name,
                                "module": name,
                            }
                        )
            elif node.type == "include_expression":
                for child in node.children:
                    if child.type == "string":
                        name = child.text.decode("utf-8").strip("'\"")
                        imports.append(
                            {
                                "name": name,
                                "module": name,
                            }
                        )

            for child in node.children:
                traverse(child)

        traverse(root)
        return imports
