# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub issue templates for bug reports, feature requests, documentation, performance, questions, and bioinformatics issues
- GitHub pull request template with comprehensive checklist
- GitHub Actions workflows for CI/CD, release management, and dependabot auto-merge
- Security policy and vulnerability reporting guidelines
- Contributing guidelines and code of conduct
- Repository settings configuration
- Dependabot configuration for automated dependency updates
- `.env.example` file with comprehensive documentation of all environment variables
- `python-dotenv` dependency for automatic `.env` file loading
- Environment setup documentation in README with API key configuration guide

### Changed
- Enhanced project documentation structure
- Updated README with detailed environment setup section and API key requirements
- DeepResearch app now automatically loads environment variables from `.env` file on startup

### Fixed
- Improved issue and PR management workflows

## [0.1.0] - 2024-01-01

### Added
- Initial release of DeepCritical
- Core workflow engine with Pydantic Graph integration
- PRIME flow for protein engineering workflows
- Bioinformatics flow for data fusion and reasoning
- DeepSearch flow for web research
- Challenge flow for experimental workflows
- Tool registry with 65+ specialized tools
- Agent system with Pydantic AI integration
- Hydra configuration management
- Comprehensive documentation and examples

### Features
- **PRIME Architecture**: Three-stage workflow (Parse → Plan → Execute)
- **Bioinformatics Integration**: Multi-source data fusion with GO, PubMed, and other databases
- **Adaptive Re-planning**: Strategic and tactical recovery mechanisms
- **Scientific Grounding**: Verifiable results from validated tools
- **Configuration Management**: Flexible Hydra-based configuration system
- **Agent Orchestration**: Multi-agent coordination for complex workflows

### Components
- **Core Workflow Engine**: Pydantic Graph-based stateful workflow execution
- **PRIME Flow**: Protein engineering with specialized tools and scientific intent detection
- **Bioinformatics Flow**: Data fusion, reasoning, and quality assessment
- **DeepSearch Flow**: Web research and information gathering
- **Tool Registry**: Comprehensive tool management and validation system
- **Agent System**: Pydantic AI-based agent communication and coordination

### Installation
```bash
# Using uv (recommended)
uv add deepcritical

# Using pip
pip install deepcritical
```

### Usage
```bash
# Basic usage
uv run deepresearch question="Your research question"

# PRIME flow
uv run deepresearch flows.prime.enabled=true question="Design a therapeutic antibody"

# Bioinformatics flow
uv run deepresearch flows.bioinformatics.enabled=true question="Analyze gene function"
```

---

## Version History

- **0.1.0**: Initial release with core functionality
- **0.2.0**: Enhanced bioinformatics workflows (planned)
- **0.3.0**: Advanced PRIME flow improvements (planned)
- **1.0.0**: Production-ready release (planned)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to this project.

## Security

See [SECURITY.md](SECURITY.md) for security policy and vulnerability reporting.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
