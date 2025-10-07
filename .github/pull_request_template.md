# Pull Request

## Description
<!-- Provide a brief description of the changes in this PR -->

## Type of Change
<!-- Mark the relevant option with an "x" -->
- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] ⚡ Performance improvement
- [ ] 🧹 Code refactoring
- [ ] 🧪 Test addition or update
- [ ] 🔧 Configuration change
- [ ] 🧬 Bioinformatics enhancement
- [ ] 🔄 Workflow improvement

## Component
<!-- Mark the relevant components with an "x" -->
- [ ] Core Workflow Engine
- [ ] PRIME Flow (Protein Engineering)
- [ ] Bioinformatics Flow (Data Fusion)
- [ ] DeepSearch Flow (Web Research)
- [ ] Challenge Flow (Experimental)
- [ ] Tool Registry
- [ ] Agent System
- [ ] Configuration (Hydra)
- [ ] Pydantic Graph
- [ ] Documentation
- [ ] Tests
- [ ] Other: <!-- specify -->

## Related Issues
<!-- Link to related issues using "Fixes #123" or "Closes #123" -->
- Fixes #
- Closes #
- Related to #

## Changes Made
<!-- Provide a detailed list of changes -->
-
-
-

## Testing
<!-- Describe the testing you've done -->
- [ ] I have tested these changes locally
- [ ] I have added/updated tests for my changes
- [ ] All existing tests pass
- [ ] I have tested with different configurations
- [ ] I have tested with different flows (PRIME, Bioinformatics, DeepSearch, etc.)

### Test Configuration
<!-- If applicable, describe the test configuration used -->
```bash
# Example test command
uv run deepresearch question="..." app_mode=single_react
```

## Configuration Changes
<!-- If this PR includes configuration changes, describe them -->
- [ ] No configuration changes
- [ ] Added new configuration options
- [ ] Modified existing configuration
- [ ] Removed configuration options

### Configuration Details
<!-- If applicable, describe the configuration changes -->
```yaml
# Example configuration changes
flows:
  new_flow:
    enabled: true
    params:
      new_param: "value"
```

## Documentation
<!-- Describe any documentation updates -->
- [ ] No documentation changes needed
- [ ] Updated README
- [ ] Updated API documentation
- [ ] Updated configuration documentation
- [ ] Added code comments
- [ ] Updated examples

## Performance Impact
<!-- Describe any performance implications -->
- [ ] No performance impact
- [ ] Performance improvement
- [ ] Performance regression (explain below)

### Performance Details
<!-- If applicable, provide performance details -->
- Execution time:
- Memory usage:
- Other metrics:

## Breaking Changes
<!-- If this is a breaking change, describe what breaks and how to migrate -->
- [ ] No breaking changes
- [ ] Breaking change (describe below)

### Migration Guide
<!-- If applicable, provide migration instructions -->

## Checklist
<!-- Mark completed items with an "x" -->
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Additional Notes
<!-- Add any additional notes, concerns, or context for reviewers -->

## Screenshots/Output
<!-- If applicable, add screenshots or example output -->

### Before
<!-- If applicable, show what it looked like before -->

### After
<!-- If applicable, show what it looks like after -->

## Reviewer Notes
<!-- Any specific areas you'd like reviewers to focus on -->
