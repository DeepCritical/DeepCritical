"""Tool registration coverage tests."""

from __future__ import annotations

import pytest
from pydantic_core import ValidationError


class TestToolRegistration:
    """Validate that tool metadata is exposed correctly."""

    @pytest.mark.pydantic_ai
    def test_tool_metadata(self, agent_bundle, collect_tool_names):
        tool_names = set(collect_tool_names)
        assert tool_names == {"web_search", "calculator"}

        for name in tool_names:
            tool = agent_bundle.agent._function_toolset.tools[name]
            assert tool.description
            assert tool.takes_ctx is True
            assert tool.function_schema.json_schema["type"] == "object"

    @pytest.mark.pydantic_ai
    def test_tool_schema_validation(self, agent_bundle):
        calculator = agent_bundle.agent._function_toolset.tools["calculator"]
        schema = calculator.function_schema
        args = schema.validator.validate_python({"numbers": [1, 2, 3]})
        assert args == {"numbers": [1, 2, 3]}

        with pytest.raises(ValidationError):
            schema.validator.validate_python({"numbers": "invalid"})
