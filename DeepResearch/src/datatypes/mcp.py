"""
MCP (Model Context Protocol) data types for DeepCritical research workflows.

This module defines Pydantic models for MCP server operations including
tool specifications, server configurations, deployment management, and Pydantic AI integration.

Pydantic AI supports MCP in two ways:
1. Agents acting as MCP clients, connecting to MCP servers to use their tools
2. Agents being used within MCP servers for enhanced tool execution

This module provides the data structures to support both patterns.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MCPServerType(str, Enum):
    """Types of MCP servers."""

    FASTQC = "fastqc"
    SAMTOOLS = "samtools"
    BOWTIE2 = "bowtie2"
    HISAT2 = "hisat2"
    STAR = "star"
    CELLRANGER = "cellranger"
    SEURAT = "seurat"
    SCANPY = "scanpy"
    BEDTOOLS = "bedtools"
    DEEPTOOLS = "deeptools"
    MACS3 = "macs3"
    HOMER = "homer"
    CUSTOM = "custom"
    BIOINFOMCP_CONVERTED = "bioinfomcp_converted"


class MCPServerStatus(str, Enum):
    """Status of MCP server deployment."""

    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"
    BUILDING = "building"
    HEALTH_CHECKING = "health_checking"


class MCPToolSpec(BaseModel):
    """Specification for an MCP tool."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    inputs: dict[str, str] = Field(
        default_factory=dict, description="Input parameter specifications"
    )
    outputs: dict[str, str] = Field(
        default_factory=dict, description="Output specifications"
    )
    version: str = Field("1.0.0", description="Tool version")
    required_tools: list[str] = Field(
        default_factory=list, description="Required external tools"
    )
    category: str = Field("general", description="Tool category")
    server_type: MCPServerType = Field(
        MCPServerType.CUSTOM, description="Type of MCP server"
    )
    command_template: str | None = Field(
        None, description="Command template for tool execution"
    )
    validation_rules: dict[str, Any] = Field(
        default_factory=dict, description="Validation rules"
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list, description="Usage examples"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "run_fastqc",
                "description": "Run FastQC quality control on FASTQ files",
                "inputs": {
                    "input_files": "List[str]",
                    "output_dir": "str",
                    "extract": "bool",
                },
                "outputs": {
                    "command_executed": "str",
                    "stdout": "str",
                    "stderr": "str",
                    "output_files": "List[str]",
                },
                "required_tools": ["fastqc"],
                "category": "quality_control",
                "server_type": "fastqc",
                "command_template": "fastqc {extract_flag} {input_files} -o {output_dir}",
                "validation_rules": {
                    "input_files": "required",
                    "output_dir": "required",
                    "extract": "boolean",
                },
                "examples": [
                    {
                        "description": "Basic FastQC analysis",
                        "parameters": {
                            "input_files": [
                                "/data/sample1.fastq",
                                "/data/sample2.fastq",
                            ],
                            "output_dir": "/results",
                            "extract": True,
                        },
                    }
                ],
            }
        }
    )


class MCPDeploymentMethod(str, Enum):
    """Methods for deploying MCP servers."""

    TESTCONTAINERS = "testcontainers"
    DOCKER_COMPOSE = "docker_compose"
    NATIVE = "native"
    KUBERNETES = "kubernetes"


class MCPToolExecutionMode(str, Enum):
    """Execution modes for MCP tools."""

    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    STREAMING = "streaming"
    BATCH = "batch"


class MCPHealthCheck(BaseModel):
    """Health check configuration for MCP servers."""

    enabled: bool = Field(True, description="Whether health checks are enabled")
    interval: int = Field(30, description="Health check interval in seconds")
    timeout: int = Field(10, description="Health check timeout in seconds")
    retries: int = Field(3, description="Number of retries before marking unhealthy")
    endpoint: str = Field("/health", description="Health check endpoint")
    expected_status: int = Field(200, description="Expected HTTP status code")


class MCPResourceLimits(BaseModel):
    """Resource limits for MCP server deployment."""

    memory: str = Field("512m", description="Memory limit (e.g., '512m', '1g')")
    cpu: float = Field(1.0, description="CPU limit (cores)")
    disk_space: str = Field("1g", description="Disk space limit")
    network_bandwidth: str | None = Field(None, description="Network bandwidth limit")


class MCPServerConfig(BaseModel):
    """Configuration for MCP server deployment."""

    server_name: str = Field(..., description="Server name")
    server_type: MCPServerType = Field(MCPServerType.CUSTOM, description="Server type")
    container_image: str = Field("python:3.11-slim", description="Docker image to use")
    working_directory: str = Field(
        "/workspace", description="Working directory in container"
    )
    environment_variables: dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    volumes: dict[str, str] = Field(default_factory=dict, description="Volume mounts")
    ports: dict[str, int] = Field(default_factory=dict, description="Port mappings")
    auto_remove: bool = Field(True, description="Auto-remove container after execution")
    network_disabled: bool = Field(False, description="Disable network access")
    privileged: bool = Field(False, description="Run container in privileged mode")
    max_execution_time: int = Field(
        300, description="Maximum execution time in seconds"
    )
    memory_limit: str = Field("512m", description="Memory limit")
    cpu_limit: float = Field(1.0, description="CPU limit")
    deployment_method: MCPDeploymentMethod = Field(
        MCPDeploymentMethod.TESTCONTAINERS, description="Deployment method"
    )
    health_check: MCPHealthCheck = Field(
        default_factory=MCPHealthCheck, description="Health check configuration"
    )
    resource_limits: MCPResourceLimits = Field(
        default_factory=MCPResourceLimits, description="Resource limits"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Server dependencies"
    )
    capabilities: list[str] = Field(
        default_factory=list, description="Server capabilities"
    )
    tool_specs: list[MCPToolSpec] = Field(
        default_factory=list, description="Available tool specifications"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "server_name": "fastqc-server",
                "server_type": "fastqc",
                "container_image": "python:3.11-slim",
                "working_directory": "/workspace",
                "environment_variables": {"PYTHONUNBUFFERED": "1"},
                "volumes": {"/host/data": "/workspace/data"},
                "ports": {"8080": 8080},
                "auto_remove": True,
                "max_execution_time": 300,
                "memory_limit": "512m",
                "cpu_limit": 1.0,
            }
        }
    )


class MCPServerDeployment(BaseModel):
    """Deployment information for MCP servers."""

    server_name: str = Field(..., description="Server name")
    server_type: MCPServerType = Field(MCPServerType.CUSTOM, description="Server type")
    container_id: str | None = Field(None, description="Container ID")
    container_name: str | None = Field(None, description="Container name")
    status: MCPServerStatus = Field(
        MCPServerStatus.PENDING, description="Deployment status"
    )
    created_at: datetime | None = Field(None, description="Creation timestamp")
    started_at: datetime | None = Field(None, description="Start timestamp")
    finished_at: datetime | None = Field(None, description="Finish timestamp")
    error_message: str | None = Field(None, description="Error message if failed")
    tools_available: list[str] = Field(
        default_factory=list, description="Available tools"
    )
    configuration: MCPServerConfig = Field(..., description="Server configuration")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "server_name": "fastqc-server",
                "server_type": "fastqc",
                "container_id": "abc123def456",
                "container_name": "mcp-fastqc-server-123",
                "status": "running",
                "tools_available": [
                    "run_fastqc",
                    "check_fastqc_version",
                    "list_fastqc_outputs",
                ],
                "configuration": {},
            }
        }
    )


class MCPExecutionContext(BaseModel):
    """Execution context for MCP tools."""

    server_name: str = Field(..., description="Name of the MCP server")
    tool_name: str = Field(..., description="Name of the tool being executed")
    execution_id: str = Field(..., description="Unique execution identifier")
    start_time: datetime = Field(
        default_factory=datetime.now, description="Execution start time"
    )
    environment_variables: dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    working_directory: str = Field("/workspace", description="Working directory")
    timeout: int = Field(300, description="Execution timeout in seconds")
    execution_mode: MCPToolExecutionMode = Field(
        MCPToolExecutionMode.SYNCHRONOUS, description="Execution mode"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class MCPToolExecutionRequest(BaseModel):
    """Request for MCP tool execution."""

    server_name: str = Field(..., description="Target server name")
    tool_name: str = Field(..., description="Tool to execute")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )
    timeout: int = Field(300, description="Execution timeout in seconds")
    async_execution: bool = Field(False, description="Execute asynchronously")
    execution_mode: MCPToolExecutionMode = Field(
        MCPToolExecutionMode.SYNCHRONOUS, description="Execution mode"
    )
    context: MCPExecutionContext | None = Field(None, description="Execution context")
    validation_required: bool = Field(
        True, description="Whether to validate parameters"
    )
    retry_on_failure: bool = Field(True, description="Whether to retry on failure")
    max_retries: int = Field(3, description="Maximum retry attempts")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "server_name": "fastqc-server",
                "tool_name": "run_fastqc",
                "parameters": {
                    "input_files": ["/data/sample1.fastq", "/data/sample2.fastq"],
                    "output_dir": "/results",
                    "extract": True,
                },
                "timeout": 300,
                "async_execution": False,
            }
        }
    )


class MCPToolExecutionResult(BaseModel):
    """Result from MCP tool execution."""

    request: MCPToolExecutionRequest = Field(..., description="Original request")
    success: bool = Field(..., description="Whether execution was successful")
    result: dict[str, Any] = Field(default_factory=dict, description="Execution result")
    execution_time: float = Field(..., description="Execution time in seconds")
    error_message: str | None = Field(None, description="Error message if failed")
    output_files: list[str] = Field(
        default_factory=list, description="Generated output files"
    )
    stdout: str = Field("", description="Standard output")
    stderr: str = Field("", description="Standard error")
    exit_code: int = Field(0, description="Process exit code")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request": {},
                "success": True,
                "result": {
                    "command_executed": "fastqc --extract /data/sample1.fastq /data/sample2.fastq",
                    "output_files": [
                        "/results/sample1_fastqc.html",
                        "/results/sample2_fastqc.html",
                    ],
                },
                "execution_time": 45.2,
                "output_files": ["/results/sample1_fastqc.html"],
                "stdout": "Started analysis of sample1.fastq...",
                "stderr": "",
                "exit_code": 0,
            }
        }
    )


class MCPBenchmarkConfig(BaseModel):
    """Configuration for MCP server benchmarking."""

    test_dataset: str = Field(..., description="Test dataset path")
    expected_outputs: dict[str, Any] = Field(
        default_factory=dict, description="Expected outputs"
    )
    performance_metrics: list[str] = Field(
        default_factory=list, description="Metrics to measure"
    )
    timeout: int = Field(300, description="Benchmark timeout")
    iterations: int = Field(3, description="Number of iterations")
    warmup_iterations: int = Field(1, description="Warmup iterations")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "test_dataset": "/data/test_fastq/",
                "expected_outputs": {
                    "output_files": ["sample1_fastqc.html", "sample1_fastqc.zip"],
                    "exit_code": 0,
                },
                "performance_metrics": ["execution_time", "memory_usage", "cpu_usage"],
                "timeout": 300,
                "iterations": 3,
                "warmup_iterations": 1,
            }
        }
    )


class MCPBenchmarkResult(BaseModel):
    """Result from MCP server benchmarking."""

    server_name: str = Field(..., description="Server name")
    config: MCPBenchmarkConfig = Field(..., description="Benchmark configuration")
    success: bool = Field(..., description="Whether benchmark was successful")
    results: list[MCPToolExecutionResult] = Field(
        default_factory=list, description="Individual results"
    )
    summary_metrics: dict[str, float] = Field(
        default_factory=dict, description="Summary metrics"
    )
    error_message: str | None = Field(None, description="Error message if failed")
    completed_at: datetime = Field(
        default_factory=datetime.now, description="Completion timestamp"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "server_name": "fastqc-server",
                "config": {},
                "success": True,
                "results": [],
                "summary_metrics": {
                    "average_execution_time": 42.3,
                    "min_execution_time": 38.1,
                    "max_execution_time": 47.8,
                    "success_rate": 1.0,
                },
                "completed_at": "2024-01-15T10:30:00Z",
            }
        }
    )


class MCPServerRegistry(BaseModel):
    """Registry of available MCP servers."""

    servers: dict[str, MCPServerDeployment] = Field(
        default_factory=dict, description="Registered servers"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )
    total_servers: int = Field(0, description="Total number of servers")

    def register_server(self, deployment: MCPServerDeployment) -> None:
        """Register a server deployment."""
        self.servers[deployment.server_name] = deployment
        self.total_servers = len(self.servers)
        self.last_updated = datetime.now()

    def get_server(self, server_name: str) -> MCPServerDeployment | None:
        """Get a server by name."""
        return self.servers.get(server_name)

    def list_servers(self) -> list[str]:
        """List all server names."""
        return list(self.servers.keys())

    def get_servers_by_type(
        self, server_type: MCPServerType
    ) -> list[MCPServerDeployment]:
        """Get servers by type."""
        return [
            deployment
            for deployment in self.servers.values()
            if deployment.server_type == server_type
        ]

    def get_running_servers(self) -> list[MCPServerDeployment]:
        """Get all running servers."""
        return [
            deployment
            for deployment in self.servers.values()
            if deployment.status == MCPServerStatus.RUNNING
        ]

    def remove_server(self, server_name: str) -> bool:
        """Remove a server from the registry."""
        if server_name in self.servers:
            del self.servers[server_name]
            self.total_servers = len(self.servers)
            self.last_updated = datetime.now()
            return True
        return False


class MCPWorkflowRequest(BaseModel):
    """Request for MCP-based workflow execution."""

    workflow_name: str = Field(..., description="Workflow name")
    servers_required: list[str] = Field(..., description="Required server names")
    input_data: dict[str, Any] = Field(default_factory=dict, description="Input data")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Workflow parameters"
    )
    timeout: int = Field(3600, description="Workflow timeout in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_name": "quality_control_pipeline",
                "servers_required": ["fastqc", "samtools"],
                "input_data": {
                    "input_files": ["/data/sample1.fastq", "/data/sample2.fastq"],
                    "reference_genome": "/data/hg38.fa",
                },
                "parameters": {
                    "quality_threshold": 20,
                    "alignment_preset": "very-sensitive",
                },
                "timeout": 3600,
            }
        }
    )


class MCPWorkflowResult(BaseModel):
    """Result from MCP workflow execution."""

    workflow_name: str = Field(..., description="Workflow name")
    success: bool = Field(..., description="Whether workflow was successful")
    server_results: dict[str, MCPToolExecutionResult] = Field(
        default_factory=dict, description="Results by server"
    )
    final_output: dict[str, Any] = Field(
        default_factory=dict, description="Final workflow output"
    )
    execution_time: float = Field(..., description="Total execution time")
    error_message: str | None = Field(None, description="Error message if failed")
    completed_at: datetime = Field(
        default_factory=datetime.now, description="Completion timestamp"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_name": "quality_control_pipeline",
                "success": True,
                "server_results": {
                    "fastqc": {},
                    "samtools": {},
                },
                "final_output": {
                    "quality_report": "/results/quality_report.html",
                    "alignment_stats": "/results/alignment_stats.txt",
                },
                "execution_time": 125.8,
                "completed_at": "2024-01-15T10:32:00Z",
            }
        }
    )


# Pydantic AI MCP Integration Types


class MCPClientConfig(BaseModel):
    """Configuration for Pydantic AI agents acting as MCP clients."""

    server_url: str = Field(..., description="URL of the MCP server")
    server_name: str = Field(..., description="Name of the MCP server")
    tools_to_import: list[str] = Field(
        default_factory=list, description="Specific tools to import from server"
    )
    connection_timeout: int = Field(30, description="Connection timeout in seconds")
    retry_attempts: int = Field(
        3, description="Number of retry attempts for failed connections"
    )
    health_check_interval: int = Field(
        60, description="Health check interval in seconds"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "server_url": "http://localhost:8000",
                "server_name": "fastqc-server",
                "tools_to_import": ["run_fastqc", "check_fastqc_version"],
                "connection_timeout": 30,
                "retry_attempts": 3,
            }
        }
    )


class MCPAgentIntegration(BaseModel):
    """Configuration for Pydantic AI agents integrated with MCP servers."""

    agent_model: str = Field(
        "anthropic:claude-sonnet-4-0", description="Model to use for the agent"
    )
    system_prompt: str = Field(..., description="System prompt for the agent")
    mcp_servers: list[MCPClientConfig] = Field(
        default_factory=list, description="MCP servers to connect to"
    )
    tool_filter: dict[str, list[str]] | None = Field(
        None, description="Filter tools by server and tool names"
    )
    execution_timeout: int = Field(300, description="Default execution timeout")
    enable_streaming: bool = Field(True, description="Enable streaming responses")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_model": "anthropic:claude-sonnet-4-0",
                "system_prompt": "You are a bioinformatics analysis assistant with access to various tools.",
                "mcp_servers": [],
                "execution_timeout": 300,
                "enable_streaming": True,
            }
        }
    )


class MCPToolCall(BaseModel):
    """Represents a tool call within MCP context."""

    tool_name: str = Field(..., description="Name of the tool being called")
    server_name: str = Field(..., description="Name of the MCP server")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )
    call_id: str = Field(..., description="Unique call identifier")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Call timestamp"
    )


class MCPToolResponse(BaseModel):
    """Response from an MCP tool call."""

    call_id: str = Field(..., description="Call identifier")
    success: bool = Field(..., description="Whether the tool call was successful")
    result: Any = Field(None, description="Tool execution result")
    error: str | None = Field(None, description="Error message if failed")
    execution_time: float = Field(..., description="Execution time in seconds")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class MCPAgentSession(BaseModel):
    """Session information for MCP-integrated Pydantic AI agents."""

    session_id: str = Field(..., description="Unique session identifier")
    agent_config: MCPAgentIntegration = Field(..., description="Agent configuration")
    connected_servers: dict[str, bool] = Field(
        default_factory=dict, description="Connection status by server"
    )
    tool_calls: list[MCPToolCall] = Field(
        default_factory=list, description="History of tool calls"
    )
    tool_responses: list[MCPToolResponse] = Field(
        default_factory=list, description="History of tool responses"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Session creation time"
    )
    last_activity: datetime = Field(
        default_factory=datetime.now, description="Last activity timestamp"
    )

    def record_tool_call(self, tool_call: MCPToolCall) -> None:
        """Record a tool call in the session."""
        self.tool_calls.append(tool_call)
        self.last_activity = datetime.now()

    def record_tool_response(self, response: MCPToolResponse) -> None:
        """Record a tool response in the session."""
        self.tool_responses.append(response)
        self.last_activity = datetime.now()

    def get_server_connection_status(self, server_name: str) -> bool:
        """Get connection status for a specific server."""
        return self.connected_servers.get(server_name, False)

    def set_server_connection_status(self, server_name: str, connected: bool) -> None:
        """Set connection status for a specific server."""
        self.connected_servers[server_name] = connected


# Enhanced MCP Support Types


class MCPErrorType(str, Enum):
    """Types of MCP-related errors."""

    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"
    DEPLOYMENT_ERROR = "deployment_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RESOURCE_ERROR = "resource_error"
    UNKNOWN_ERROR = "unknown_error"


class MCPErrorDetails(BaseModel):
    """Detailed error information for MCP operations."""

    error_type: MCPErrorType = Field(..., description="Type of error")
    error_code: str | None = Field(None, description="Error code")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Error timestamp"
    )
    server_name: str | None = Field(
        None, description="Name of the server where error occurred"
    )
    tool_name: str | None = Field(
        None, description="Name of the tool where error occurred"
    )
    stack_trace: str | None = Field(None, description="Stack trace if available")


class MCPMetrics(BaseModel):
    """Metrics for MCP server and tool performance."""

    server_name: str = Field(..., description="Server name")
    tool_name: str | None = Field(None, description="Tool name")
    execution_count: int = Field(0, description="Number of executions")
    success_count: int = Field(0, description="Number of successful executions")
    failure_count: int = Field(0, description="Number of failed executions")
    average_execution_time: float = Field(
        0.0, description="Average execution time in seconds"
    )
    total_execution_time: float = Field(
        0.0, description="Total execution time in seconds"
    )
    last_execution_time: datetime | None = Field(
        None, description="Last execution timestamp"
    )
    peak_memory_usage: int = Field(0, description="Peak memory usage in bytes")
    cpu_usage_percent: float = Field(0.0, description="CPU usage percentage")

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.execution_count
        return self.success_count / total if total > 0 else 0.0

    def record_execution(self, success: bool, execution_time: float) -> None:
        """Record a tool execution."""
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        self.total_execution_time += execution_time
        self.average_execution_time = self.total_execution_time / self.execution_count
        self.last_execution_time = datetime.now()


class MCPHealthStatus(BaseModel):
    """Health status for MCP servers."""

    server_name: str = Field(..., description="Server name")
    status: str = Field(..., description="Health status (healthy, unhealthy, unknown)")
    last_check: datetime = Field(
        default_factory=datetime.now, description="Last health check timestamp"
    )
    response_time: float | None = Field(None, description="Response time in seconds")
    error_message: str | None = Field(None, description="Error message if unhealthy")
    version: str | None = Field(None, description="Server version")
    uptime_seconds: int | None = Field(None, description="Server uptime in seconds")


class MCPWorkflowStep(BaseModel):
    """A step in an MCP-based workflow."""

    step_id: str = Field(..., description="Unique step identifier")
    step_name: str = Field(..., description="Human-readable step name")
    server_name: str = Field(..., description="MCP server to use")
    tool_name: str = Field(..., description="Tool to execute")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Step dependencies"
    )
    timeout: int = Field(300, description="Step timeout in seconds")
    retry_count: int = Field(0, description="Number of retries attempted")
    max_retries: int = Field(3, description="Maximum number of retries")
    status: str = Field(
        "pending", description="Step status (pending, running, completed, failed)"
    )
    result: dict[str, Any] | None = Field(None, description="Step execution result")
    error: str | None = Field(None, description="Error message if failed")
    execution_time: float | None = Field(None, description="Execution time in seconds")
    started_at: datetime | None = Field(None, description="Step start timestamp")
    completed_at: datetime | None = Field(None, description="Step completion timestamp")


class MCPWorkflowExecution(BaseModel):
    """Execution state for MCP-based workflows."""

    workflow_id: str = Field(..., description="Unique workflow identifier")
    workflow_name: str = Field(..., description="Workflow name")
    steps: list[MCPWorkflowStep] = Field(
        default_factory=list, description="Workflow steps"
    )
    status: str = Field("pending", description="Workflow status")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    started_at: datetime | None = Field(None, description="Start timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    total_execution_time: float | None = Field(None, description="Total execution time")
    error_message: str | None = Field(None, description="Error message if failed")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def get_pending_steps(self) -> list[MCPWorkflowStep]:
        """Get steps that are pending execution."""
        return [step for step in self.steps if step.status == "pending"]

    def get_completed_steps(self) -> list[MCPWorkflowStep]:
        """Get steps that have completed successfully."""
        return [step for step in self.steps if step.status == "completed"]

    def get_failed_steps(self) -> list[MCPWorkflowStep]:
        """Get steps that have failed."""
        return [step for step in self.steps if step.status == "failed"]
