# API Reference

This section provides comprehensive API documentation for DeepCritical's core modules and components.

## Core Modules

### Agents API
Complete documentation for the agent system including specialized agents, orchestrators, and workflow management.

**[→ Agents API Documentation](agents.md)**

- `AgentType` - Agent type enumeration
- `AgentDependencies` - Agent configuration and dependencies
- `BaseAgent` - Abstract base class for all agents
- `AgentOrchestrator` - Multi-agent coordination
- `CodeExecutionAgent` - Code execution and improvement
- `CodeGenerationAgent` - Natural language to code conversion
- `CodeImprovementAgent` - Error analysis and code enhancement

### Tools API
Documentation for the tool ecosystem, registry system, and execution framework.

**[→ Tools API Documentation](tools.md)**

- `ToolRunner` - Abstract base class for tools
- `ToolSpec` - Tool specification and metadata
- `ToolRegistry` - Global tool registry and management
- `ExecutionResult` - Tool execution results
- `ToolRequest`/`ToolResponse` - Tool communication interfaces

## Data Types

### Agent Framework Types
Core types for agent communication and state management.

**[→ Agent Framework Types](../api/datatypes.md)**

- `AgentRunResponse` - Agent execution response
- `ChatMessage` - Message format for agent communication
- `Role` - Message roles (user, assistant, system)
- `Content` - Message content types
- `TextContent` - Text message content

### Research Types
Types for research workflows and data structures.

**[→ Research Types](datatypes.md)**

- `ResearchState` - Main research workflow state
- `ResearchOutcome` - Research execution results
- `StepResult` - Individual step execution results
- `ExecutionHistory` - Workflow execution tracking

## Configuration API

### Hydra Configuration
Configuration management and validation system.

**[→ Configuration API](configuration.md)**

- Configuration file structure
- Environment variable integration
- Configuration validation
- Dynamic configuration composition

## Tool Categories

### Knowledge Query Tools
Tools for information retrieval and knowledge querying.

**[→ Knowledge Query Tools](../user-guide/tools/knowledge-query.md)**

### Sequence Analysis Tools
Bioinformatics tools for sequence analysis and processing.

**[→ Sequence Analysis Tools](../user-guide/tools/bioinformatics.md)**

### Structure Prediction Tools
Molecular structure prediction and modeling tools.

**[→ Structure Prediction Tools](../user-guide/tools/bioinformatics.md)**

### Molecular Docking Tools
Drug-target interaction and docking simulation tools.

**[→ Molecular Docking Tools](../user-guide/tools/bioinformatics.md)**

### De Novo Design Tools
Novel molecule design and generation tools.

**[→ De Novo Design Tools](../user-guide/tools/bioinformatics.md)**

### Function Prediction Tools
Protein function annotation and prediction tools.

**[→ Function Prediction Tools](../user-guide/tools/bioinformatics.md)**

## Specialized APIs

### Bioinformatics Integration
APIs for bioinformatics data sources and integration.

**[→ Bioinformatics API](../user-guide/tools/bioinformatics.md)**

### RAG System API
Retrieval-augmented generation system interfaces.

**[→ RAG API](../user-guide/tools/rag.md)**

### Search Integration API
Web search and content processing APIs.

**[→ Search API](../user-guide/tools/search.md)**

## MCP Server Framework

### MCP Server Base Classes
Base classes for Model Context Protocol server implementations.

**[→ MCP Server Base Classes](../api/tools.md#enhanced-mcp-server-framework)**

- `MCPServerBase` - Enhanced base class with Pydantic AI integration
- `@mcp_tool` - Custom decorator for Pydantic AI tool creation
- `MCPServerConfig` - Server configuration management

### Available MCP Servers
29 pre-built bioinformatics MCP servers with containerized deployment.

**[→ Available MCP Servers](../api/tools.md#available-mcp-servers)**

## Development APIs

### Testing Framework
APIs for comprehensive testing and validation.

**[→ Testing API](../development/testing.md)**

### CI/CD Integration
APIs for continuous integration and deployment.

**[→ CI/CD API](../development/ci-cd.md)**

## Navigation

- **[Getting Started](../getting-started/quickstart.md)** - Basic usage and setup
- **[Architecture](../architecture/overview.md)** - System design and components
- **[Examples](../examples/basic.md)** - Usage examples and tutorials
- **[Development](../development/setup.md)** - Development environment and workflow
