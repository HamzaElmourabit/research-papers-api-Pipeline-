# Contributing to Research Papers Pipeline

Thank you for your interest in contributing! Here's how you can help.

---

## How to Contribute

### 1. Fork the Repository
```bash
# Click "Fork" button on GitHub
git clone https://github.com/YOUR_USERNAME/research-papers-pipeline.git
cd research-papers-pipeline
```

### 2. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 3. Make Your Changes
- Follow Python PEP 8 style guide
- Add docstrings to functions
- Write tests if applicable

### 4. Test Your Changes
```bash
# Run tests
python -m pytest tests/

# Check style
python -m pylint ingestion/ pipelines/ casandra/

# Type checking
python -m mypy .
```

### 5. Commit and Push
```bash
git add .
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name
```

### 6. Create Pull Request
- Go to GitHub
- Click "New Pull Request"
- Describe your changes
- Wait for review

---

## Development Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install with dev dependencies
pip install -r requirements.txt
pip install pytest pylint mypy black

# Format code
black ingestion/ pipelines/ casandra/

# Run tests
pytest tests/ -v
```

---

## Areas for Contribution

- 🐛 **Bug fixes** - Found an issue? Report or fix it
- 📚 **Documentation** - Improve README, guides, or docstrings
- ✨ **Features** - New data sources, transformations, or exports
- 🧪 **Tests** - Add unit or integration tests
- 🚀 **Performance** - Optimize pipeline efficiency
- 🔐 **Security** - Report security issues privately

---

## Code Style Guidelines

### Python
```python
# Good
def validate_paper(paper: dict) -> bool:
    """
    Validate paper against schema.
    
    Args:
        paper: Paper dictionary
        
    Returns:
        True if valid, False otherwise
    """
    return paper.get("arxiv_id") is not None


# Avoid
def check(p):
    return p.get("arxiv_id")
```

### Docstrings
```python
def fetch_papers(categories: list, batch_size: int = 100) -> list:
    """
    Fetch papers from arXiv API.
    
    Args:
        categories: List of arXiv categories (e.g., ["cs.AI", "cs.LG"])
        batch_size: Number of papers per request
        
    Returns:
        List of paper dictionaries
        
    Raises:
        ConnectionError: If API is unavailable
        ValueError: If categories list is empty
    """
    pass
```

---

## Commit Message Format

```
type: subject

body (optional)

footer (optional)
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `style:` Code style (no logic changes)
- `refactor:` Code restructuring
- `perf:` Performance improvement
- `test:` Test additions
- `chore:` Build, dependencies, etc.

**Example:**
```
feat: add email notifications for pipeline failures

- Send email on ETL validation errors
- Add configurable recipient list
- Include error details in message

Closes #42
```

---

## Pull Request Checklist

Before submitting:
- [ ] Code follows style guidelines
- [ ] Self-reviewed changes
- [ ] Added comments for complex logic
- [ ] Updated relevant documentation
- [ ] Added tests (if applicable)
- [ ] All tests pass
- [ ] No new warnings

---

## Questions?

- **Documentation**: See [docs/](docs/) folder
- **Issues**: Check [GitHub Issues](https://github.com/YOUR_USERNAME/research-papers-pipeline/issues)
- **Discussions**: Start a GitHub Discussion

---

## Community Guidelines

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Share knowledge and best practices

Thank you for contributing! 🙏
