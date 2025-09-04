# Contributing to D365FO MCP Server

Thank you for your interest in contributing to the D365 Finance & Operations MCP Server! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Architecture Overview](#architecture-overview)
- [Making Contributions](#making-contributions)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

This project adheres to a code of conduct that we expect all participants to uphold. Please be respectful, inclusive, and constructive in all interactions.

### Our Pledge

- Use welcoming and inclusive language
- Respect differing viewpoints and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- **Python 3.10+** (3.11+ recommended)
- **uv** package manager (recommended) or pip
- **Git** for version control
- **Access to D365FO environment** for testing (demo/sandbox preferred)
- **Azure AD Service Principal** for authentication

### First-Time Setup

```bash
# Clone the repository
git clone https://github.com/your-org/d365fo-mcp.git
cd d365fo-mcp

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install development dependencies
uv sync --extra dev

# Copy environment template
cp .env.example .env
# Edit .env with your D365FO credentials

# Initialize database
python -m d365fo_mcp.main --init-db

# Verify setup
python -m d365fo_mcp.main --validate
```

## Development Setup

### Environment Configuration

Create a `.env` file with your development settings:

```bash
# D365 Authentication (Required)
AZURE_CLIENT_ID=your-dev-client-id
AZURE_CLIENT_SECRET=your-dev-secret
AZURE_TENANT_ID=your-tenant-id
D365_BASE_URL=https://your-env.sandbox.operations.dynamics.com

# Development Settings
DATAAREAID=usmf
DATABASE_PATH=./data/d365fo-mcp-dev.db
LOG_LEVEL=debug
DEBUG=true
SQLITE_ECHO=false
```

### Development Tools

```bash
# Code formatting
ruff format .

# Linting
ruff check . --fix

# Type checking
mypy src/d365fo_mcp

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/d365fo_mcp --cov-report=html

# Run specific test category
pytest tests/unit/
pytest tests/integration/
```

## Architecture Overview

The project follows a dependency injection architecture with clear separation of concerns:

```
src/d365fo_mcp/
├── config.py              # Configuration management
├── di_container.py         # Dependency injection container
├── factories/             # Object creation patterns
├── auth/                  # Authentication providers
├── client/                # D365FO API clients
├── repositories/          # Data access layer
│   ├── metadata/          # Entity metadata operations
│   ├── instructions/      # Learning system data
│   └── sqlite/           # SQLite implementation
├── services/             # Business logic layer
│   ├── metadata/         # Entity discovery & caching
│   └── instructions/     # AI instruction management
└── tools/                # MCP protocol implementation
```

### Key Principles

1. **Interface-Based Design**: Every major component has an interface
2. **Dependency Injection**: Central DIContainer manages all dependencies
3. **Repository Pattern**: Data access abstracted through repositories
4. **Factory Pattern**: Complex object construction via factories
5. **Service Layer**: Business logic separated from data access

## Making Contributions

### Types of Contributions

- 🐛 **Bug Fixes**: Fix existing functionality issues
- ✨ **New Features**: Add new MCP tools or capabilities
- 🏗️ **Architecture**: Improve system design and patterns
- 📚 **Documentation**: Enhance guides, examples, and API docs
- 🧪 **Testing**: Add or improve test coverage
- 🔧 **Infrastructure**: DevOps, CI/CD, tooling improvements

### Finding Issues to Work On

- Check the [Issues page](https://github.com/your-org/d365fo-mcp/issues)
- Look for `good-first-issue` labels for newcomers
- Look for `help-wanted` labels for community contributions
- Check the project roadmap for planned features

### Before Starting Work

1. **Check existing issues** to avoid duplicate work
2. **Create an issue** if none exists for your contribution
3. **Discuss your approach** in the issue comments
4. **Get approval** for significant changes before coding

## Pull Request Process

### 1. Create Feature Branch

```bash
# Create and switch to feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Your Changes

- Follow the [coding standards](#coding-standards)
- Write tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 3. Test Your Changes

```bash
# Run full test suite
pytest

# Test specific components
pytest tests/repositories/
pytest tests/services/

# Integration tests with D365FO
pytest tests/integration/ -m "not slow"

# Manual testing
python -m d365fo_mcp.main --validate
```

### 4. Submit Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Create pull request via GitHub UI
```

### 5. Pull Request Requirements

- [ ] **Clear description** of changes and motivation
- [ ] **Tests added/updated** for new functionality
- [ ] **Documentation updated** if needed
- [ ] **All CI checks pass** (tests, linting, type checking)
- [ ] **No breaking changes** without major version bump
- [ ] **Performance impact assessed** for critical paths

### Pull Request Template

```markdown
## Description
Brief description of changes and why they're needed.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that breaks existing functionality)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance impact assessed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Code is well-commented
- [ ] Documentation updated
- [ ] No breaking changes or changelog updated
```

## Coding Standards

### Python Style Guide

- **PEP 8** compliance with line length up to 100 characters
- **Type hints** required for all public APIs
- **Docstrings** for all public functions and classes
- **Structured logging** using structlog

### Code Formatting

```bash
# Format code (required before commit)
ruff format .

# Fix linting issues
ruff check . --fix
```

### Type Checking

```bash
# Type check (required before commit)
mypy src/d365fo_mcp
```

### Naming Conventions

- **Classes**: PascalCase (`MetadataService`)
- **Functions**: snake_case (`get_entity_metadata`)
- **Constants**: UPPER_SNAKE_CASE (`DEFAULT_TIMEOUT`)
- **Private members**: Leading underscore (`_internal_method`)

### Import Organization

```python
# Standard library imports
import json
from typing import Dict, Any, Optional

# Third-party imports
import httpx
import structlog

# Local imports
from ..config import get_settings
from .interface import IMetadataService
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                   # Fast, isolated tests
│   ├── repositories/
│   ├── services/
│   └── tools/
├── integration/            # Tests with external dependencies
│   ├── test_d365_client.py
│   └── test_auth_provider.py
└── fixtures/               # Shared test data and mocks
```

### Test Categories

- **Unit Tests**: Fast, isolated, no external dependencies
- **Integration Tests**: Test with real D365FO (use sandbox)
- **Performance Tests**: Measure critical path performance
- **Contract Tests**: Verify interface compliance

### Writing Tests

```python
import pytest
from unittest.mock import Mock, AsyncMock

from src.d365fo_mcp.services.metadata import MetadataService


class TestMetadataService:
    """Test MetadataService business logic"""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock repository for testing"""
        repo = AsyncMock()
        repo.search_entities.return_value = [{"name": "TestEntity"}]
        return repo
    
    @pytest.fixture  
    def service(self, mock_repository):
        """Service instance with mocked dependencies"""
        return MetadataService(mock_repository)
    
    @pytest.mark.asyncio
    async def test_search_entities_returns_formatted_results(self, service):
        """Test that search returns properly formatted results"""
        results = await service.search_entities("Test")
        
        assert len(results) == 1
        assert results[0]["name"] == "TestEntity"
```

### Test Execution

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/d365fo_mcp --cov-report=html

# Run specific test file
pytest tests/unit/services/test_metadata_service.py

# Run tests matching pattern
pytest -k "test_search"

# Run integration tests (requires D365FO access)
pytest tests/integration/ -m "not slow"
```

## Documentation

### Types of Documentation

1. **Code Documentation**: Docstrings, type hints, comments
2. **API Documentation**: Tool interfaces and usage examples
3. **Architecture Documentation**: System design and patterns
4. **User Documentation**: Setup, configuration, troubleshooting

### Documentation Standards

- **Docstrings**: Google style for all public APIs
- **Type Hints**: Complete coverage for public interfaces
- **Examples**: Working code examples in docstrings
- **Comments**: Explain "why" not "what" for complex logic

### Example Documentation

```python
async def search_entities(
    self, 
    pattern: str, 
    limit: int = 20, 
    skip: int = 0
) -> List[Dict[str, Any]]:
    """
    Search for D365FO entities by name pattern with relevance scoring.
    
    Args:
        pattern: Search term to match against entity names
        limit: Maximum number of results to return (default: 20, max: 100)
        skip: Number of results to skip for pagination (default: 0)
        
    Returns:
        List of entity dictionaries with relevance scores, sorted by relevance.
        Each entity contains: name, description, use_for_queries, relevance.
        
    Raises:
        ServiceError: If search fails due to repository or validation issues
        
    Example:
        >>> results = await service.search_entities("Customer", limit=10)
        >>> print(f"Found {len(results)} entities")
        >>> for entity in results:
        ...     print(f"- {entity['name']} (relevance: {entity['relevance']})")
    """
```

## Community

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests, questions
- **GitHub Discussions**: Community discussions, design decisions
- **Pull Request Reviews**: Code review and feedback

### Getting Help

1. **Search existing issues** for similar problems
2. **Check documentation** for configuration and usage
3. **Create a new issue** with detailed information:
   - Environment details (Python version, OS, D365FO version)
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and logs

### Issue Templates

Use the provided issue templates for:
- 🐛 Bug reports
- ✨ Feature requests
- 🙋 Questions and help requests
- 📖 Documentation improvements

## Release Process

### Versioning

We follow [Semantic Versioning (SemVer)](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

- [ ] Version number updated in `pyproject.toml`
- [ ] Changelog updated with all changes
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Migration guide for breaking changes
- [ ] Release notes prepared

---

## Questions?

If you have questions about contributing, please:

1. Check this guide and the project documentation
2. Search existing GitHub issues and discussions
3. Create a new issue with the `question` label

Thank you for contributing to D365FO MCP Server! 🎉