# Contributing to The Knowledge Garage

First off, thanks for taking the time to contribute! 🎉

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

- Ensure the bug was not already reported by searching on GitHub under [Issues](https://github.com/yourusername/knowledge-garage/issues).
- If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/yourusername/knowledge-garage/issues/new). Be sure to include:
  - A clear title and description
  - Steps to reproduce the issue
  - Expected vs. actual behavior
  - Screenshots if applicable
  - Your operating system and Python version

### Suggesting Enhancements

- Open a new issue with the `enhancement` label
- Clearly describe the feature and why it would be useful
- Include any relevant screenshots or mockups

### Pull Requests

1. Fork the repository and create your branch from `main`
2. Install the development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Make your changes
4. Run the tests:
   ```bash
   pytest
   ```
5. Ensure your code follows the project's style guide
6. Update the documentation if needed
7. Submit a pull request with a clear description of your changes

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/knowledge-garage.git
   cd knowledge-garage
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
5. Run the application:
   ```bash
   python knowledge_garage.py
   ```

## Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code
- Use docstrings for all public modules, functions, and classes
- Keep lines under 88 characters (PEP 8)
- Use type hints for better code documentation

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
