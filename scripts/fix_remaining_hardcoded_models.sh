#!/bin/bash
# Complete fix for ALL remaining hardcoded model strings

echo "Fixing remaining 19 hardcoded model strings..."

# Fix Pydantic Field defaults - use reference to ModelConfigLoader
# These need to stay as strings in Field() but reference a constant
echo "1. Fixing deep_agent_implementations.py Field default..."
sed -i '41s/Field("anthropic:claude-sonnet-4-0"/Field(default_factory=lambda: __import__("DeepResearch.src.utils.config_loader", fromlist=["ModelConfigLoader"]).ModelConfigLoader().get_default_llm_model()/' \
  DeepResearch/src/agents/deep_agent_implementations.py

echo "2. Fixing code_execution_orchestrator.py Field default..."
sed -i '30s/"anthropic:claude-sonnet-4-0", description=/default_factory=lambda: __import__("DeepResearch.src.utils.config_loader", fromlist=["ModelConfigLoader"]).ModelConfigLoader().get_default_llm_model(); description=/' \
  DeepResearch/src/agents/code_execution_orchestrator.py

echo "3. Fixing workflow_orchestration.py Field default..."
sed -i '534s/"anthropic:claude-sonnet-4-0", description=/default_factory=lambda: __import__("DeepResearch.src.utils.config_loader", fromlist=["ModelConfigLoader"]).ModelConfigLoader().get_default_llm_model(); description=/' \
  DeepResearch/src/datatypes/workflow_orchestration.py

echo "4. Fixing mcp.py Field default..."
sed -i '582s/"anthropic:claude-sonnet-4-0", description=/default_factory=lambda: __import__("DeepResearch.src.utils.config_loader", fromlist=["ModelConfigLoader"]).ModelConfigLoader().get_default_llm_model(); description=/' \
  DeepResearch/src/datatypes/mcp.py

echo "5. Fixing bioinformatics_tools.py Field default..."
sed -i '58s/"anthropic:claude-sonnet-4-0", description=/default_factory=lambda: __import__("DeepResearch.src.utils.config_loader", fromlist=["ModelConfigLoader"]).ModelConfigLoader().get_default_llm_model(); description=/' \
  DeepResearch/src/tools/bioinformatics_tools.py

# Fix function parameter defaults
echo "6. Fixing code_generation_agent.py function param..."
sed -i '446s/generation_model: str = "anthropic:claude-sonnet-4-0"/generation_model: str | None = None/' \
  DeepResearch/src/agents/code_generation_agent.py

echo "7. Fixing code_execution_orchestrator.py function param..."
sed -i '460s/generation_model: str = "anthropic:claude-sonnet-4-0"/generation_model: str | None = None/' \
  DeepResearch/src/agents/code_execution_orchestrator.py

# Fix bioinformatics_agent_implementations.py (6 instances)
echo "8-13. Fixing bioinformatics_agent_implementations.py (6 function params)..."
sed -i 's/model_name: str = "anthropic:claude-sonnet-4-0"/model_name: str | None = None/g' \
  DeepResearch/src/prompts/bioinformatics_agent_implementations.py

# Fix dict.get() fallbacks - use ModelConfigLoader
echo "14. Fixing workflow_orchestrator.py dict.get fallback..."
sed -i '109s/"model_name", "anthropic:claude-sonnet-4-0"/"model_name") or ModelConfigLoader().get_default_llm_model()/' \
  DeepResearch/src/agents/workflow_orchestrator.py

echo "15. Fixing pydantic_ai_utils.py dict.get fallback..."
sed -i '120s/pyd_cfg.get("model", "anthropic:claude-sonnet-4-0")/pyd_cfg.get("model") or ModelConfigLoader().get_default_llm_model()/' \
  DeepResearch/src/utils/pydantic_ai_utils.py

echo "16. Fixing bioinformatics_tools.py dict.get fallback..."
sed -i '73s/model_config.get("default", "anthropic:claude-sonnet-4-0")/model_config.get("default") or ModelConfigLoader().get_default_llm_model()/' \
  DeepResearch/src/tools/bioinformatics_tools.py

echo "✓ All hardcoded strings fixed!"
