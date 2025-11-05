import importlib.util
import pathlib
import sys

import pytest


class TestPydanticGraphFallbacks:
    """Tests for fallback placeholder classes when pydantic_graph is unavailable."""

    @pytest.fixture(autouse=True)
    def fake_import_context(self, mocker):
        """Force ImportError path for pydantic_graph and dynamically import fallback module."""
        mocker.patch.dict(sys.modules, {"pydantic_graph": None})

        # Build full path to the target file
        module_path = pathlib.Path(
            "DeepResearch/src/statemachines/workflow_pattern_statemachines.py"
        ).resolve()
        spec = importlib.util.spec_from_file_location(
            "statemachines_fallback_test", module_path
        )

        # Type checker protection
        assert spec is not None, f"Cannot load spec for {module_path}"
        assert spec.loader is not None, f"No loader found for {module_path}"

        module = importlib.util.module_from_spec(spec)
        sys.modules["statemachines_fallback_test"] = module
        spec.loader.exec_module(module)

        self.module = module
        yield
        sys.modules.pop("pydantic_graph", None)
        sys.modules.pop("statemachines_fallback_test", None)

    def test_fallback_classes_exist(self):
        for name in ["BaseNode", "Edge", "End", "Graph", "GraphRunContext"]:
            assert hasattr(self.module, name)
            assert isinstance(getattr(self.module, name), type)

    @pytest.mark.parametrize(
        "cls_name", ["BaseNode", "Edge", "End", "Graph", "GraphRunContext"]
    )
    def test_fallback_classes_instantiable(self, cls_name):
        cls = getattr(self.module, cls_name)
        obj = cls("foo", bar="baz")
        assert isinstance(obj, cls)

    def test_base_node_is_generic(self):
        BaseNode = self.module.BaseNode
        assert hasattr(BaseNode, "__parameters__")
        assert BaseNode.__parameters__[0].__name__ == "T"

    def test_fallback_classes_are_isolated(self):
        classes = [
            self.module.BaseNode,
            self.module.Edge,
            self.module.End,
            self.module.Graph,
            self.module.GraphRunContext,
        ]
        assert len({cls.__name__ for cls in classes}) == len(classes)
