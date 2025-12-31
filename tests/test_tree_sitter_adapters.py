"""Tree-sitter language adapter tests for Repository Intelligence Scanner."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.adapters.language_adapter_manager import LanguageAdapterManager
from src.adapters.tree_sitter_python_adapter import TreeSitterPythonAdapter
from src.adapters.tree_sitter_javascript_adapter import TreeSitterJavaScriptAdapter
from src.adapters.tree_sitter_csharp_adapter import TreeSitterCSharpAdapter
from src.adapters.tree_sitter_php_adapter import TreeSitterPHPAdapter
from src.adapters.tree_sitter_ruby_adapter import TreeSitterRubyAdapter
from src.adapters.tree_sitter_swift_adapter import TreeSitterSwiftAdapter
from src.adapters.tree_sitter_kotlin_adapter import TreeSitterKotlinAdapter
from src.adapters.tree_sitter_scala_adapter import TreeSitterScalaAdapter
from src.adapters.tree_sitter_rust_adapter import TreeSitterRustAdapter


class TestTreeSitterPythonAdapter:
    """Test Tree-sitter Python language adapter functionality."""

    def test_python_adapter_extract_ast_invalid_file(self):
        """Test Python AST extraction with invalid file path."""
        adapter = TreeSitterPythonAdapter()
        result = adapter.extract_ast("")
        assert "error" in result
        assert result["imports"] == []
        assert result["classes"] == []

    def test_python_adapter_extract_ast_valid_file(self, tmp_path):
        """Test Python AST extraction with valid file."""
        # Create a test Python file
        test_file = tmp_path / "test.py"
        test_content = (
            "import os\n"
            "from typing import List\n"
            "\n"
            "class TestClass:\n"
            "    def __init__(self, value):\n"
            "        self.value = value\n"
            "\n"
            "    def method(self):\n"
            "        return \"value: \" + str(self.value)\n"
            "\n"
            "def test_function(x, y):\n"
            "    return [x]\n"
            "\n"
            "variable = \"test\"\n"
        )
        test_file.write_text(test_content)

        adapter = TreeSitterPythonAdapter()
        assert adapter.initialize_parser()
        result = adapter.extract_ast(str(test_file))

        assert "error" not in result
        assert result["file_path"] == str(test_file)
        assert len(result["classes"]) > 0
        assert len(result["functions"]) > 0
        assert len(result["variables"]) > 0


class TestTreeSitterJavaScriptAdapter:
    """Test Tree-sitter JavaScript/TypeScript language adapter functionality."""

    def test_javascript_adapter_extract_ast_valid_file(self, tmp_path):
        """Test JavaScript AST extraction with valid file."""
        test_file = tmp_path / "test.js"
        test_content = (
            "import React from 'react';\n"
            "const { useState } = require('react');\n"
            "\n"
            "class TestComponent extends React.Component {\n"
            "    constructor(props) {\n"
            "        super(props);\n"
            "        this.state = { count: 0 };\n"
            "    }\n"
            "\n"
            "    render() {\n"
            "        return <div>{this.state.count}</div>;\n"
            "    }\n"
            "}\n"
            "\n"
            "function testFunction(x, y) {\n"
            "    return x + y;\n"
            "}\n"
            "\n"
            "const arrowFunc = (a, b) => a * b;\n"
            "let variable = 'test';\n"
        )
        test_file.write_text(test_content)

        adapter = TreeSitterJavaScriptAdapter()
        assert adapter.initialize_parser()
        result = adapter.extract_ast(str(test_file))

        assert "error" not in result
        assert result["file_path"] == str(test_file)
        assert len(result["imports"]) > 0
        assert len(result["classes"]) > 0
        assert len(result["functions"]) > 0


class TestTreeSitterCSharpAdapter:
    """Test Tree-sitter C# language adapter functionality."""

    def test_csharp_adapter_extract_ast_valid_file(self, tmp_path):
        """Test C# AST extraction with valid file."""
        test_file = tmp_path / "test.cs"
        test_content = (
            "using System;\n"
            "using System.Collections.Generic;\n"
            "\n"
            "namespace TestNamespace {\n"
            "    public class TestClass : BaseClass {\n"
            "        private int _value;\n"
            "\n"
            "        public TestClass(int value) {\n"
            "            _value = value;\n"
            "        }\n"
            "\n"
            "        public void TestMethod() {\n"
            "            Console.WriteLine(_value);\n"
            "        }\n"
            "    }\n"
            "\n"
            "    public static void TestFunction(string input) {\n"
            "        var result = input.ToUpper();\n"
            "    }\n"
            "}\n"
        )
        test_file.write_text(test_content)

        adapter = TreeSitterCSharpAdapter()
        assert adapter.initialize_parser()
        result = adapter.extract_ast(str(test_file))

        assert "error" not in result
        assert result["file_path"] == str(test_file)
        assert len(result["imports"]) > 0
        assert len(result["classes"]) > 0


class TestTreeSitterPHPAdapter:
    """Test Tree-sitter PHP language adapter functionality."""

    def test_php_adapter_extract_ast_valid_file(self, tmp_path):
        """Test PHP AST extraction with valid file."""
        test_file = tmp_path / "test.php"
        test_content = (
            "<?php\n"
            "require_once 'config.php';\n"
            "include 'functions.php';\n"
            "\n"
            "class TestClass extends BaseClass {\n"
            "    private $value;\n"
            "\n"
            "    public function __construct($value) {\n"
            "        $this->value = $value;\n"
            "    }\n"
            "\n"
            "    public function testMethod() {\n"
            "        return $this->value;\n"
            "    }\n"
            "}\n"
            "\n"
            "function testFunction($x, $y) {\n"
            "    return $x + $y;\n"
            "}\n"
            "\n"
            "$variable = 'test';\n"
            "?>\n"
        )
        test_file.write_text(test_content)

        adapter = TreeSitterPHPAdapter()
        assert adapter.initialize_parser()
        result = adapter.extract_ast(str(test_file))

        assert "error" not in result
        assert result["file_path"] == str(test_file)
        assert len(result["classes"]) > 0
        assert len(result["functions"]) > 0


class TestTreeSitterRubyAdapter:
    """Test Tree-sitter Ruby language adapter functionality."""

    def test_ruby_adapter_extract_ast_valid_file(self, tmp_path):
        """Test Ruby AST extraction with valid file."""
        test_file = tmp_path / "test.rb"
        test_content = (
            "require 'json'\n"
            "require_relative 'config'\n"
            "\n"
            "class TestClass < BaseClass\n"
            "    def initialize(value)\n"
            "        @value = value\n"
            "    end\n"
            "\n"
            "    def test_method\n"
            "        puts @value\n"
            "    end\n"
            "end\n"
            "\n"
            "def test_function(x, y)\n"
            "    x + y\n"
            "end\n"
            "\n"
            "variable = 'test'\n"
        )
        test_file.write_text(test_content)

        adapter = TreeSitterRubyAdapter()
        assert adapter.initialize_parser()
        result = adapter.extract_ast(str(test_file))

        assert "error" not in result
        assert result["file_path"] == str(test_file)
        assert len(result["classes"]) > 0
        assert len(result["functions"]) > 0


class TestTreeSitterSwiftAdapter:
    """Test Tree-sitter Swift language adapter functionality."""

    def test_swift_adapter_extract_ast_valid_file(self, tmp_path):
        """Test Swift AST extraction with valid file."""
        test_file = tmp_path / "test.swift"
        test_content = (
            "import Foundation\n"
            "import UIKit\n"
            "\n"
            "class TestClass: UIViewController {\n"
            "    private var value: Int\n"
            "\n"
            "    init(value: Int) {\n"
            "        self.value = value\n"
            "        super.init(nibName: nil, bundle: nil)\n"
            "    }\n"
            "\n"
            "    func testMethod() {\n"
            "        print(value)\n"
            "    }\n"
            "}\n"
            "\n"
            "func testFunction(x: Int, y: Int) -> Int {\n"
            "    return x + y\n"
            "}\n"
            "\n"
            "let variable = \"test\"\n"
        )
        test_file.write_text(test_content)

        adapter = TreeSitterSwiftAdapter()
        assert adapter.initialize_parser()
        result = adapter.extract_ast(str(test_file))

        assert "error" not in result
        assert result["file_path"] == str(test_file)
        assert len(result["classes"]) > 0
        assert len(result["functions"]) > 0


class TestTreeSitterKotlinAdapter:
    """Test Tree-sitter Kotlin language adapter functionality."""

    def test_kotlin_adapter_extract_ast_valid_file(self, tmp_path):
        """Test Kotlin AST extraction with valid file."""
        test_file = tmp_path / "test.kt"
        test_content = (
            "import java.util.*\n"
            "import kotlin.collections.List\n"
            "\n"
            "class TestClass : BaseClass() {\n"
            "    private var value: Int = 0\n"
            "\n"
            "    constructor(value: Int) {\n"
            "        this.value = value\n"
            "    }\n"
            "\n"
            "    fun testMethod() {\n"
            "        println(value)\n"
            "    }\n"
            "}\n"
            "\n"
            "fun testFunction(x: Int, y: Int): Int {\n"
            "    return x + y\n"
            "}\n"
            "\n"
            "val variable = \"test\"\n"
        )
        test_file.write_text(test_content)

        adapter = TreeSitterKotlinAdapter()
        assert adapter.initialize_parser()
        result = adapter.extract_ast(str(test_file))

        assert "error" not in result
        assert result["file_path"] == str(test_file)
        assert len(result["classes"]) > 0
        assert len(result["functions"]) > 0


class TestTreeSitterScalaAdapter:
    """Test Tree-sitter Scala language adapter functionality."""

    def test_scala_adapter_extract_ast_valid_file(self, tmp_path):
        """Test Scala AST extraction with valid file."""
        test_file = tmp_path / "test.scala"
        test_content = (
            "import scala.collection.mutable.ListBuffer\n"
            "import java.util.{Date, Calendar}\n"
            "\n"
            "class TestClass extends BaseClass {\n"
            "    private var value: Int = 0\n"
            "\n"
            "    def testMethod(): Unit = {\n"
            "        println(value)\n"
            "    }\n"
            "}\n"
            "\n"
            "object TestObject {\n"
            "    def testFunction(x: Int, y: Int): Int = {\n"
            "        x + y\n"
            "    }\n"
            "}\n"
            "\n"
            "val variable = \"test\"\n"
        )
        test_file.write_text(test_content)

        adapter = TreeSitterScalaAdapter()
        assert adapter.initialize_parser()
        result = adapter.extract_ast(str(test_file))

        assert "error" not in result
        assert result["file_path"] == str(test_file)
        assert len(result["classes"]) > 0
        assert len(result["functions"]) > 0


class TestLanguageAdapterManager:
    """Test language adapter manager functionality."""

    def test_manager_initialization(self):
        """Test that manager initializes with expected adapters."""
        manager = LanguageAdapterManager()
        assert len(manager.adapters) > 0

        # Check that common extensions are supported
        assert '.py' in manager.adapters
        assert '.js' in manager.adapters
        assert '.java' in manager.adapters
        assert '.cs' in manager.adapters

    def test_get_supported_languages(self):
        """Test getting list of supported languages."""
        manager = LanguageAdapterManager()
        languages = manager.get_supported_languages()
        assert len(languages) >= 10  # Should support at least 10 languages

        # Check some expected languages
        assert 'python' in languages
        assert 'javascript' in languages
        assert 'java' in languages
        assert 'rust' in languages  # Verify Rust support

    def test_get_adapter_for_file(self):
        """Test getting adapter for specific file types."""
        manager = LanguageAdapterManager()

        assert manager.get_adapter_for_file('test.py') is not None
        assert manager.get_adapter_for_file('test.js') is not None
        assert manager.get_adapter_for_file('test.java') is not None
        assert manager.get_adapter_for_file('test.rs') is not None  # Test Rust support
        assert manager.get_adapter_for_file('unknown.xyz') is None

    def test_manager_rust_integration(self, tmp_path):
        """Test manager integration with Rust files."""
        # Create a test Rust file
        test_file = tmp_path / "integration.rs"
        test_content = (
            "#[derive(Debug)]\n"
            "struct TestStruct<'a, T> {\n"
            "    field: &'a T,\n"
            "}\n"
            "\n"
            "unsafe fn test_unsafe() {\n"
            "    // unsafe code\n"
            "}\n"
            "\n"
            "fn safe_function() {\n"
            "    unsafe {\n"
            "        // unsafe block\n"
            "    }\n"
            "}\n"
        )
        test_file.write_text(test_content)

        manager = LanguageAdapterManager()
        adapter = manager.get_adapter_for_file(str(test_file))
        
        assert adapter is not None
        assert isinstance(adapter, TreeSitterRustAdapter)
        
        result = adapter.extract_ast(str(test_file))
        
        assert "error" not in result
        assert len(result["classes"]) >= 1  # struct
        assert len(result["unsafe_blocks"]) >= 2  # unsafe function + unsafe block
        assert len(result["attributes"]) >= 1  # derive attribute
        assert len(result["generics"]) >= 1  # generic parameter T
        assert len(result["lifetimes"]) >= 1  # lifetime 'a


class TestTreeSitterRustAdapter:
    """Test Tree-sitter Rust language adapter functionality."""

    def test_rust_adapter_extract_ast_invalid_file(self):
        """Test Rust AST extraction with invalid file path."""
        adapter = TreeSitterRustAdapter()
        result = adapter.extract_ast("")
        assert "error" in result
        assert result["imports"] == []
        assert result["classes"] == []
        assert result["functions"] == []

    def test_rust_adapter_extract_ast_valid_file(self, tmp_path):
        """Test Rust AST extraction with valid file."""
        # Create a test Rust file
        test_file = tmp_path / "test.rs"
        test_content = (
            "fn main() {\n"
            "    println!(\"Hello, world!\");\n"
            "}\n"
            "\n"
            "struct User {\n"
            "    name: String,\n"
            "    age: u32,\n"
            "}\n"
            "\n"
            "enum Status {\n"
            "    Active,\n"
            "    Inactive,\n"
            "}\n"
            "\n"
            "use std::collections::HashMap;\n"
        )
        test_file.write_text(test_content)

        adapter = TreeSitterRustAdapter()
        adapter.initialize_parser()
        result = adapter.extract_ast(str(test_file))

        assert "error" not in result
        assert result["file_path"] == str(test_file)
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "main"
        assert len(result["classes"]) == 2  # User struct and Status enum
        assert len(result["imports"]) == 1
        assert result["imports"][0]["path"] == "std::collections::HashMap"
        assert result["complexity"] >= 1
        
        # Check new advanced analysis fields
        assert "unsafe_blocks" in result
        assert "lifetimes" in result
        assert "generics" in result
        assert "attributes" in result
    def test_rust_adapter_advanced_features(self, tmp_path):
        """Test Rust adapter advanced analysis features."""
        # Create a test Rust file with advanced features
        test_file = tmp_path / "advanced.rs"
        test_content = (
            "#[derive(Debug, Clone)]\n"
            "struct User<'a, T> {\n"
            "    name: &'a str,\n"
            "    data: T,\n"
            "}\n"
            "\n"
            "impl<'a, T> User<'a, T> {\n"
            "    fn new(name: &'a str, data: T) -> Self {\n"
            "        User { name, data }\n"
            "    }\n"
            "}\n"
            "\n"
            "const MAX_SIZE: usize = 1024;\n"
            "static mut COUNTER: u32 = 0;\n"
            "\n"
            "unsafe fn dangerous_operation() {\n"
            "    COUNTER += 1;\n"
            "}\n"
        )
        test_file.write_text(test_content)

        adapter = TreeSitterRustAdapter()
        adapter.initialize_parser()
        result = adapter.extract_ast(str(test_file))

        assert "error" not in result
        assert len(result["classes"]) >= 1  # User struct
        assert len(result["unsafe_blocks"]) >= 1  # unsafe function
        assert len(result["generics"]) >= 1  # Generic parameters
        assert len(result["attributes"]) >= 1  # derive attribute
        assert len(result["lifetimes"]) >= 1  # 'a lifetime
        assert len(result["variables"]) >= 2  # const and static

    def test_rust_adapter_initialization(self):
        """Test Rust adapter initialization."""
        adapter = TreeSitterRustAdapter()
        assert adapter.language_name == "rust"
        assert ".rs" in adapter.file_extensions
        assert adapter.initialize_parser() is True
        assert adapter.parser is not None

    def test_rust_adapter_build_dependency_graph(self, tmp_path):
        """Test Rust dependency graph building."""
        # Create a mock Cargo.toml
        cargo_file = tmp_path / "Cargo.toml"
        cargo_content = (
            "[package]\n"
            "name = \"test\"\n"
            "version = \"0.1.0\"\n"
            "\n"
            "[dependencies]\n"
            "serde = \"1.0\"\n"
            "tokio = { version = \"1.0\", features = [\"full\"] }\n"
        )
        cargo_file.write_text(cargo_content)

        adapter = TreeSitterRustAdapter()
        graph = adapter.build_dependency_graph(str(tmp_path))

        assert "crates" in graph
        assert "serde" in graph["crates"]
        assert "tokio" in graph["crates"]
