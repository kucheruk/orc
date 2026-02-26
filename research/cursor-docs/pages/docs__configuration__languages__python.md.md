# Python

This guide was heavily inspired by [Jack Fields](https://x.com/OrdinaryInds)
and his
[article](https://medium.com/ordinaryindustries/the-ultimate-vs-code-setup-for-python-538026b34d94)
about setting up VS Code for Python development. Please check his article for
more details.

## Prerequisites

Before we begin, ensure you have:

- [Python](https://python.org) installed (3.8 or higher recommended)
- [Git](https://git-scm.com/) for version control
- Cursor installed and updated to the latest version

## Essential Extensions

The following extensions setup Cursor to be fully featured for Python development. These provide you with syntax highlighting, linting, debugging and unit testing.

- [**Python**](cursor:extension/ms-python.python) (Core language support from Microsoft)
- [**Cursor Pyright**](cursor:extension/anysphere.cursorpyright) (Fast Python language server)
- [**Python Debugger**](cursor:extension/ms-python.debugpy) (Enhanced debugging capabilities)
- [**Ruff**](cursor:extension/charliermarsh.ruff) (Python linter and formatter)

### Advanced Python Tooling

While the above extensions have previously been the most popular extensions for Python development in Cursor, we've also added some additional extensions that can help you get the most out of your Python development.

#### `uv` - Python Environment Manager

[uv](https://github.com/astral-sh/uv) is a modern Python package manager that can be used to create and manage virtual environments, in addition to replacing pip as the default package manager.

To install uv, run the following command in your terminal:

```bash
pip install uv
```

#### `ruff` - Python Linter and Formatter

[Ruff](https://docs.astral.sh/ruff/) is a modern Python linter and formatter that can be used to check for programming errors, helps enforce coding standards, and can suggest refactoring. It can be used alongside Black for code formatting.

To install Ruff, run the following command in your terminal:

```bash
pip install ruff
```

## Cursor Configuration

### 1. Python Interpreter

Configure your Python interpreter in Cursor:

1. Open Command Palette (Cmd/Ctrl + Shift + P)
2. Search for "Python: Select Interpreter"
3. Choose your Python interpreter (or virtual environment if you're using one)

### 2. Code Formatting

Set up automatic code formatting with Black:

Black is a code formatter that automatically formats your code to follow a
consistent style. It requires zero configuration and is widely adopted in the
Python community.

To install Black, run the following command in your terminal:

```bash
pip install black
```

Then, configure Cursor to use Black for code formatting, by adding the following to your `settings.json` file:

```json
{
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.formatting.blackArgs": ["--line-length", "88"]
}
```

### 3. Linting

We can use PyLint to check for programming errors, helps enforce coding standards, and can suggest refactoring.

To install PyLint, run the following command in your terminal:

```bash
pip install pylint
```

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.lintOnSave": true
}
```

### 4. Type Checking

In addition to linting, we can use MyPy to check for type errors.

To install MyPy, run the following command in your terminal:

```bash
pip install mypy
```

```json
{
  "python.linting.mypyEnabled": true
}
```

## Debugging

Cursor provides powerful debugging capabilities for Python:

1. Set breakpoints by clicking the gutter
2. Use the Debug panel (Cmd/Ctrl + Shift + D)
3. Configure `launch.json` for custom debug configurations

## Framework Support

Cursor works seamlessly with popular Python frameworks:

- **Web Frameworks**: Django, Flask, FastAPI
- **Data Science**: Jupyter, NumPy, Pandas
- **Machine Learning**: TensorFlow, PyTorch, scikit-learn
- **Testing**: pytest, unittest
- **API**: requests, aiohttp
- **Database**: SQLAlchemy, psycopg2


---

## Sitemap

[Overview of all docs pages](/llms.txt)
