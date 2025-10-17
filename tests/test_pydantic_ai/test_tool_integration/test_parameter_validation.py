"""Parameter validation tests for tool schemas."""

from __future__ import annotations

import pytest
from pydantic_core import ValidationError


class TestToolParameterValidation:
    """Ensure tool schemas enforce expected types."""

    @pytest.mark.pydantic_ai
    def test_valid_parameters(self, agent_bundle):
        calculator = agent_bundle.agent._function_toolset.tools["calculator"]
        args = calculator.function_schema.validator.validate_python({"numbers": [5, 7]})
        assert args == {"numbers": [5, 7]}

    @pytest.mark.pydantic_ai
    def test_invalid_parameters_raise(self, agent_bundle):
        calculator = agent_bundle.agent._function_toolset.tools["calculator"]
        with pytest.raises(ValidationError):
            calculator.function_schema.validator.validate_python({"numbers": "oops"})
