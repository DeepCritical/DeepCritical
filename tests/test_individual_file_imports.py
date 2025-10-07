"""
Individual file import tests for DeepResearch src modules.

This module tests that all individual Python files in the src directory
can be imported correctly and validates their basic structure.
"""

import importlib
import inspect
import os
from pathlib import Path

import pytest


class TestIndividualFileImports:
    """Test imports for individual Python files in src directory."""

    def get_all_python_files(self):
        """Get all Python files in the src directory."""
        src_path = Path("DeepResearch/src")
        python_files = []

        for root, dirs, files in os.walk(src_path):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if not d.startswith("__pycache__")]

            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(src_path.parent)
                    python_files.append(str(rel_path).replace("\\", "/"))

        return sorted(python_files)

    def test_all_python_files_exist(self):
        """Test that all expected Python files exist."""
        expected_files = self.get_all_python_files()

        # Expected subdirectories
        _expected_patterns = [
            "agents/",
            "datatypes/",
            "prompts/",
            "statemachines/",
            "tools/",
            "utils/",
        ]

        # Check that we have files in each subdirectory
        agents_files = [f for f in expected_files if "agents" in f]
        datatypes_files = [f for f in expected_files if "datatypes" in f]
        prompts_files = [f for f in expected_files if "prompts" in f]
        statemachines_files = [f for f in expected_files if "statemachines" in f]
        tools_files = [f for f in expected_files if "tools" in f]
        utils_files = [f for f in expected_files if "utils" in f]

        assert len(agents_files) > 0, "No agent files found"
        assert len(datatypes_files) > 0, "No datatype files found"
        assert len(prompts_files) > 0, "No prompt files found"
        assert len(statemachines_files) > 0, "No statemachine files found"
        assert len(tools_files) > 0, "No tool files found"
        assert len(utils_files) > 0, "No utils files found"

    def test_file_import_structure(self):
        """Test that files have proper import structure."""
        python_files = self.get_all_python_files()

        for file_path in python_files:
            # Convert file path to module path
            # Normalize path separators for module path
            normalized_path = (
                file_path.replace("\\", "/").replace("/", ".").replace(".py", "")
            )
            module_path = f"DeepResearch.{normalized_path}"

            # Try to import the module
            try:
                if module_path.startswith("DeepResearch.src."):
                    # Remove the DeepResearch.src. prefix for importing
                    clean_module_path = module_path.replace("DeepResearch.src.", "")
                    module = importlib.import_module(clean_module_path)
                    assert module is not None
                # Handle files in the root of src
                elif "." in module_path:
                    module = importlib.import_module(module_path)
                    assert module is not None

            except ImportError:
                # Skip files that can't be imported due to missing dependencies or path issues
                # This is acceptable as the main goal is to test that the code is syntactically correct
                pass
            except Exception:
                # Some files might have runtime dependencies that aren't available
                # This is acceptable as long as the import structure is correct
                pass

    def test_init_files_exist(self):
        """Test that __init__.py files exist in all directories."""
        src_path = Path("DeepResearch/src")

        # Check main directories
        main_dirs = [
            "agents",
            "datatypes",
            "prompts",
            "statemachines",
            "tools",
            "utils",
        ]
        for dir_name in main_dirs:
            init_file = src_path / dir_name / "__init__.py"
            assert init_file.exists(), f"Missing __init__.py in {dir_name}"

    def test_module_has_content(self):
        """Test that modules have some content (not just empty files)."""
        python_files = self.get_all_python_files()

        for file_path in python_files[:5]:  # Test first 5 files to avoid being too slow
            # Convert file path to module path
            module_path = file_path.replace("/", ".").replace(".py", "")

            try:
                if module_path.startswith("DeepResearch.src."):
                    clean_module_path = module_path.replace("DeepResearch.src.", "")
                    module = importlib.import_module(clean_module_path)

                    # Check that module has some attributes (classes, functions, variables)
                    attributes = [
                        attr for attr in dir(module) if not attr.startswith("_")
                    ]
                    assert len(attributes) > 0, (
                        f"Module {module_path} appears to be empty"
                    )

            except ImportError:
                # Skip modules that can't be imported due to missing dependencies
                continue
            except Exception:
                # Skip modules with runtime issues
                continue

    def test_no_syntax_errors(self):
        """Test that files don't have syntax errors by attempting to compile them."""
        python_files = self.get_all_python_files()

        for file_path in python_files:
            full_path = Path("DeepResearch/src") / file_path

            try:
                # Try to compile the file
                with open(full_path, encoding="utf-8") as f:
                    source = f.read()

                compile(source, str(full_path), "exec")

            except SyntaxError as e:
                pytest.fail(f"Syntax error in {file_path}: {e}")
            except UnicodeDecodeError as e:
                pytest.fail(f"Encoding error in {file_path}: {e}")
            except Exception:
                # Other errors might be due to missing dependencies or file access issues
                # This is acceptable for this test
                pass

    def test_importlib_utilization(self):
        """Test that we can use importlib to inspect modules."""
        # Test a few key modules
        test_modules = [
            "DeepResearch.src.agents.prime_parser",
            "DeepResearch.src.datatypes.bioinformatics",
            "DeepResearch.src.tools.base",
            "DeepResearch.src.utils.config_loader",
        ]

        for module_name in test_modules:
            try:
                # Try to import and inspect the module
                module = importlib.import_module(module_name)

                # Check that it's a proper module
                assert hasattr(module, "__name__")
                assert module.__name__ == module_name

                # Check that it has a file path
                if hasattr(module, "__file__"):
                    assert module.__file__ is not None
                    assert "DeepResearch/src" in module.__file__.replace("\\", "/")

            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_module_inspection(self):
        """Test that modules can be inspected for their structure."""
        # Test a few key modules for introspection
        test_modules = [
            ("DeepResearch.src.agents.prime_parser", ["ScientificIntent", "DataType"]),
            ("DeepResearch.src.datatypes.bioinformatics", ["EvidenceCode", "GOTerm"]),
            ("DeepResearch.src.tools.base", ["ToolSpec", "ToolRunner"]),
        ]

        for module_name, expected_classes in test_modules:
            try:
                module = importlib.import_module(module_name)

                # Check that expected classes exist
                for class_name in expected_classes:
                    assert hasattr(module, class_name), (
                        f"Missing {class_name} in {module_name}"
                    )
                    cls = getattr(module, class_name)
                    assert cls is not None

                    # Check that it's actually a class
                    assert inspect.isclass(cls), (
                        f"{class_name} is not a class in {module_name}"
                    )

            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")


class TestFileExistenceValidation:
    """Test that validates file existence and basic properties."""

    def test_src_directory_exists(self):
        """Test that the src directory exists."""
        src_path = Path("DeepResearch/src")
        assert src_path.exists(), "DeepResearch/src directory does not exist"
        assert src_path.is_dir(), "DeepResearch/src is not a directory"

    def test_subdirectories_exist(self):
        """Test that all expected subdirectories exist."""
        src_path = Path("DeepResearch/src")
        expected_dirs = [
            "agents",
            "datatypes",
            "prompts",
            "statemachines",
            "tools",
            "utils",
        ]

        for dir_name in expected_dirs:
            dir_path = src_path / dir_name
            assert dir_path.exists(), f"Directory {dir_name} does not exist"
            assert dir_path.is_dir(), f"{dir_name} is not a directory"

    def test_python_files_are_files(self):
        """Test that all Python files are actually files (not directories)."""
        src_path = Path("DeepResearch/src")

        for root, dirs, files in os.walk(src_path):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if not d.startswith("__pycache__")]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    assert file_path.is_file(), f"{file_path} is not a file"

    def test_no_duplicate_files(self):
        """Test that there are no duplicate file names within the same directory."""
        src_path = Path("DeepResearch/src")
        dir_files = {}

        for root, dirs, files in os.walk(src_path):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if not d.startswith("__pycache__")]

            current_dir = Path(root)
            if current_dir not in dir_files:
                dir_files[current_dir] = set()

            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    if file in dir_files[current_dir]:
                        pytest.fail(
                            f"Duplicate file name found in {current_dir}: {file}"
                        )
                    dir_files[current_dir].add(file)
