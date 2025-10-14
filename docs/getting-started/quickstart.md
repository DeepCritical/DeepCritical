# Quick Start

This guide will help you get started with DeepCritical in just a few minutes.

## 1. Basic Usage

DeepCritical uses a simple command-line interface. The most basic way to use it is:

```bash
uv run deepresearch question="What is machine learning?"
```

This will run DeepCritical with default settings and provide a comprehensive analysis of your question.

## 2. Enabling Specific Flows

DeepCritical supports multiple research flows. You can enable specific flows using Hydra configuration:

```bash
# Enable PRIME flow for protein engineering
uv run deepresearch flows.prime.enabled=true question="Design a therapeutic antibody for SARS-CoV-2"

# Enable bioinformatics flow for data analysis
uv run deepresearch flows.bioinformatics.enabled=true question="What is the function of TP53 gene?"

# Enable deep search for web research
uv run deepresearch flows.deepsearch.enabled=true question="Latest advances in quantum computing"
```

## 3. Multiple Flows

You can enable multiple flows simultaneously:

```bash
uv run deepresearch \
  flows.prime.enabled=true \
  flows.bioinformatics.enabled=true \
  question="Analyze protein structure and function relationships"
```

## 4. Advanced Configuration

For more control, use configuration files:

```bash
# Use specific configuration
uv run deepresearch --config-name=config_with_modes question="Your research question"

# Custom configuration with parameters
uv run deepresearch \
  --config-name=config_with_modes \
  question="Advanced research query" \
  flows.prime.params.adaptive_replanning=true \
  flows.prime.params.manual_confirmation=false
```

## 5. Batch Processing

Run multiple questions in batch mode:

```bash
# Multiple questions
uv run deepresearch \
  --multirun \
  question="First question",question="Second question" \
  flows.prime.enabled=true

# Using a batch file
uv run deepresearch \
  --config-path=configs \
  --config-name=batch_config
```

## 6. Development Mode

For development and testing:

```bash
# Run in development mode with additional logging
uv run deepresearch \
  question="Test query" \
  hydra.verbose=true \
  flows.prime.params.debug=true

# Test specific components
make test

# Run with coverage
make test-cov
```

## 7. Output and Results

DeepCritical generates comprehensive outputs:

- **Console Output**: Real-time progress and results
- **Log Files**: Detailed execution logs in `outputs/`
- **Reports**: Generated reports in various formats
- **Artifacts**: Data files, plots, and analysis results

## 8. Tools {#tools}

### Tool Ecosystem

DeepCritical provides a rich ecosystem of specialized tools organized by functionality:

- **Knowledge Query Tools**: Web search, database queries, knowledge base access
- **Sequence Analysis Tools**: BLAST searches, multiple alignments, motif discovery
- **Structure Prediction Tools**: AlphaFold, homology modeling, quality assessment
- **Molecular Docking Tools**: Drug-target interaction analysis
- **Analytics Tools**: Statistical analysis, data visualization, machine learning

### Using Tools

Tools are automatically available to agents and workflows:

```bash
# Tools are used automatically in research workflows
uv run deepresearch flows.prime.enabled=true question="Design a protein with specific binding properties"
```

### Tool Configuration

Configure tool behavior in your configuration files:

```yaml
# Tool-specific configuration
tool_configs:
  web_search:
    max_results: 20
    timeout: 30
  bioinformatics_tools:
    blast:
      e_value_threshold: 1e-5
```

## 10. Next Steps

After your first successful run:

1. **Explore Flows**: Try different combinations of flows for your use case
2. **Customize Configuration**: Modify `configs/` files for your specific needs
3. **Add Tools**: Extend the tool registry with custom tools
4. **Contribute**: Join the development community

## 11. Getting Help

- **Documentation**: Browse this documentation site
- **Issues**: Report bugs or request features on GitHub
- **Discussions**: Join community discussions
- **Examples**: Check the examples directory for usage patterns

## 12. Troubleshooting

If you encounter issues:

1. **Check Logs**: Look in `outputs/` directory for detailed error messages
2. **Verify Dependencies**: Ensure all dependencies are installed correctly
3. **Check Configuration**: Validate your Hydra configuration files
4. **Update System**: Make sure you have the latest version

For more detailed information, see the [Configuration Guide](configuration.md) and [Architecture Overview](../architecture/overview.md).
