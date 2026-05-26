# Contributing to emachines

Welcome, and thank you for wanting to contribute! This document is the **single source of truth** for everything you need to know: setting up your environment, writing code, running tests, and getting your work merged.

If something is unclear, open a [Discussion](https://github.com/NaveenDeepak/emachines/discussions) before filing an issue — chances are it'll help the next contributor too.

---

## Table of Contents

1. [Before You Start](#1-before-you-start)
2. [Toolchain — What You Need Installed](#2-toolchain--what-you-need-installed)
3. [Setting Up Your Environment](#3-setting-up-your-environment)
4. [Working with VS Code + Docker](#4-working-with-vs-code--docker)
5. [Development Workflow](#5-development-workflow)
6. [Code Standards](#6-code-standards)
7. [Testing](#7-testing)
8. [Branch & Commit Conventions](#8-branch--commit-conventions)
9. [Opening a Pull Request](#9-opening-a-pull-request)
10. [Review & Merge Process](#10-review--merge-process)
11. [Common Commands Reference](#11-common-commands-reference)
12. [Getting Help](#12-getting-help)

---

## 1. Before You Start

- **Check existing issues and PRs** to avoid duplicate work.
- For new features or significant changes, **open an issue first** and get a thumbs-up before writing code.
- All contributions must go through a Pull Request — direct pushes to `main` are blocked.

---

## 2. Toolchain — What You Need Installed

This is the complete checklist. Every contributor needs these; nothing else is required on your local machine because everything else runs inside Docker.

### Required

| Tool | Purpose | Install |
|------|---------|---------|
| **Git ≥ 2.39** | Version control | [git-scm.com](https://git-scm.com/) |
| **Docker Desktop** (macOS / Windows) *or* **Docker Engine** (Linux) | Runs the development container | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| **VS Code** | IDE (strongly recommended; see §4) | [code.visualstudio.com](https://code.visualstudio.com/) |
| **VS Code "Dev Containers" extension** | Opens VS Code *inside* Docker | ID: `ms-vscode-remote.remote-containers` |

### Verification checklist

Run these commands in your terminal **before** proceeding:

```bash
git --version          # should print 2.x.x or higher
docker --version       # should print 20.x or higher
docker compose version # should print v2.x.x (note: no hyphen)
```

If any command fails, install the tool from the link in the table above.

> **Windows users:** Docker Desktop requires WSL2. Enable it from Docker Desktop → Settings → General → "Use the WSL2 based engine". Then clone the repo *inside* WSL2 (not on the Windows filesystem) for best performance.

---

## 3. Setting Up Your Environment

### Step 1 — Fork and clone

```bash
# Fork the repo on GitHub first, then:
git clone https://github.com/<your-username>/emachines.git
cd emachines

# Add the upstream remote so you can pull future changes
git remote add upstream https://github.com/NaveenDeepak/emachines.git
```

### Step 2 — Choose your workflow

There are two ways to develop. **Option A (recommended)** integrates VS Code directly with Docker. **Option B** is for terminal-only contributors.

---

## 4. Working with VS Code + Docker

This is the recommended workflow. VS Code opens a full IDE session *inside* the container, so your editor, linter, formatter, and Jupyter kernel all use exactly the same Python environment as CI.

### First-time setup

1. Install the **Dev Containers** extension (`ms-vscode-remote.remote-containers`).
2. Open the `emachines` folder in VS Code (`File → Open Folder`).
3. VS Code will show a blue notification: **"Reopen in Container"** — click it.
   - Alternatively: `Cmd/Ctrl+Shift+P` → **"Dev Containers: Reopen in Container"**.
4. VS Code builds the Docker image (first time: ~2–3 minutes) and reopens inside the container.
5. All recommended extensions install automatically (see `.devcontainer/devcontainer.json`).

After that, every time you open the folder VS Code will offer to reopen in the container. The build is cached so subsequent starts take a few seconds.

### What you get inside the container

- Python 3.10 with all project dependencies pre-installed
- Black, isort, flake8, mypy running as you type and on save
- Jupyter kernel wired to the correct environment
- Pre-commit hooks installed automatically
- Port 8888 forwarded so you can open JupyterLab in your browser

### Running JupyterLab from VS Code

Open the **VS Code terminal** (`` Ctrl+` ``) and run:

```bash
jupyter lab --ip=0.0.0.0 --allow-root --no-browser
```

Then open `http://localhost:8888` in your browser. Use the token printed in the terminal.

### Recommended extensions

When you open the project, VS Code will prompt you to install the recommended extensions. Accept the prompt, or install them manually via `Cmd/Ctrl+Shift+P` → **"Extensions: Show Recommended Extensions"**.

The list lives in `.vscode/extensions.json`. Key ones:

| Extension | Why |
|-----------|-----|
| `ms-python.python` + `ms-python.vscode-pylance` | Python language support |
| `ms-toolsai.jupyter` | Edit and run `.ipynb` files |
| `ms-python.black-formatter` | Format on save |
| `ms-python.isort` | Sort imports on save |
| `ms-python.flake8` | Inline linting |
| `ms-python.mypy-type-checker` | Inline type errors |
| `eamodio.gitlens` | Git blame, history, branch view |
| `github.vscode-pull-request-github` | Review PRs inside VS Code |
| `njpwerner.autodocstring` | Generate docstring stubs |

---

## 5. Development Workflow

This project uses **nbdev**: notebooks are the source of truth, and Python modules are generated from them.

### The golden rule

> Edit notebooks in `nbs/`. Never edit the generated files in `emachines/` directly — your changes will be overwritten.

### Step-by-step

```
1. Pull latest main
       ↓
2. Create a feature branch
       ↓
3. Open JupyterLab (or VS Code notebook editor)
       ↓
4. Edit / create a notebook in nbs/
       ↓
5. Run nbdev-export  →  updates emachines/*.py
       ↓
6. Run pytest tests/
       ↓
7. Commit notebooks + generated files together
       ↓
8. Push branch → open PR
```

### Notebook structure (required)

Every module notebook must follow this four-section pattern:

```
### Section Title
[Theory / math — equations, physics, references]
[Implementation — functions marked #| export, with type hints and docstrings]
[Examples — concrete numerical examples showing usage]
[Tests — assert statements validating correctness]
```

Theory goes **immediately before** the function it explains, not in a separate block at the top.

### nbdev directives

```python
#| default_exp module_name   # sets the output module for this notebook
#| export                    # export this function/class to the module
#| hide                      # run but don't show in docs (use for test cells)
```

### Building the library

```bash
# Inside the container terminal or VS Code terminal:
nbdev-export          # export notebooks → emachines/*.py
```

Always run `nbdev-export` before committing. The CI pipeline will fail if the notebooks and generated files are out of sync.

---

## 6. Code Standards

### Python style

| Standard | Tool | Config |
|----------|------|--------|
| PEP 8 + formatting | **black** | `--line-length 100` |
| Import ordering | **isort** | `--profile black --line-length 100` |
| Linting | **flake8** | `--max-line-length 100 --extend-ignore E203,W503` |
| Type checking | **mypy** | `--ignore-missing-imports` |

### Pre-commit hooks

Pre-commit runs all of the above automatically before every commit. It is installed automatically inside the container. If a hook fails, it will tell you what to fix; fix it, `git add` the changed files, and commit again.

```bash
# Install manually if needed:
pre-commit install

# Run against all files at any time:
pre-commit run --all-files
```

### Type hints and docstrings

All public functions and classes must have:

- Type hints on every parameter and the return value
- A docstring in Google style

```python
#| export
def winding_factor(slots: int, poles: int, harmonic: int = 1) -> float:
    """Calculate the winding factor for a distributed winding.

    Args:
        slots: Number of stator slots.
        poles: Number of magnetic poles.
        harmonic: Harmonic order (default 1 = fundamental).

    Returns:
        Winding factor between 0 and 1.

    Raises:
        ValueError: If slots or poles are not positive integers.
    """
    if slots <= 0 or poles <= 0:
        raise ValueError("slots and poles must be positive")
    ...
```

### Scientific notation

For physics-heavy functions, include the governing equation in the docstring or in a preceding markdown cell:

```python
"""
Uses the pitch factor formula:
    k_p = sin(α_p · π / 2)
where α_p = coil_pitch / pole_pitch.
"""
```

---

## 7. Testing

### Test locations

| Where | When |
|-------|------|
| `assert` cells inside notebooks (`#| hide`) | Quick checks during development |
| `tests/test_*.py` | Regression tests that run in CI |

### Running tests

```bash
# All tests
pytest tests/

# Specific file
pytest tests/test_winding.py

# Verbose output
pytest tests/ -v

# With coverage
pytest tests/ --cov=emachines --cov-report=term-missing
```

### Test requirements

- New functions need at least one test in `tests/`.
- Tests must be deterministic (no randomness without a fixed seed).
- Test function names: `test_<what_it_checks>`.
- Test file names: `test_<module_name>.py`.

---

## 8. Branch & Commit Conventions

### Branch names

```
feature/<short-description>     # new capability
fix/<short-description>         # bug fix
docs/<short-description>        # documentation only
refactor/<short-description>    # restructuring, no behaviour change
test/<short-description>        # adding or fixing tests
```

Examples: `feature/ipmsm-reluctance-model`, `fix/iron-loss-negative-flux`, `docs/improve-setup-guide`

**Never commit directly to `main`.** Branch protection will reject it.

### Commit messages

Follow the imperative mood, present tense:

```
Add reluctance torque model for IPMSM

- Implements Ld/Lq saliency ratio calculation
- Adds pitch and distribution factor for q-axis winding
- Validates against published FEA results from [Ref]

Closes #42
```

- First line: ≤ 50 characters, imperative mood, no period.
- Blank line after the first line if you add a body.
- Body: wrap at 72 characters, explain *why* not just *what*.
- Reference related issues with `Closes #N` or `Refs #N`.

**Bad commit messages:** `fix`, `update`, `wip`, `asdf`, `changes`

### Keeping your branch up to date

```bash
git fetch upstream
git rebase upstream/main
```

Prefer rebase over merge to keep a clean history.

---

## 9. Opening a Pull Request

### Before you open a PR, verify:

- [ ] Branch is up to date with `main` (`git fetch upstream && git rebase upstream/main`)
- [ ] `nbdev-export` has been run and generated files are committed
- [ ] `pytest tests/` passes locally
- [ ] `pre-commit run --all-files` passes with no errors
- [ ] Notebooks have markdown explanations, not just code
- [ ] New functions have type hints, docstrings, and tests
- [ ] No secrets, API keys, or passwords in any file

### PR title

Use the same imperative style as commit messages:

```
Add IPMSM reluctance torque model
Fix negative flux crash in iron loss calculation
```

### PR description

Use the template that appears automatically (`.github/pull_request_template.md`). Fill in every section — an incomplete description will delay review.

### Draft PRs

If your work is not ready for review, open it as a **Draft PR**. This signals "in progress" and keeps the PR visible without triggering a review request. Convert to "Ready for review" when it is done.

---

## 10. Review & Merge Process

### What the maintainer looks at

1. **CI must be green** — all four jobs (lint, typecheck, test, notebooks) pass.
2. **Physics correctness** — does the implementation match the documented equations?
3. **Code quality** — type hints, docstrings, readable variable names.
4. **Notebook quality** — is the theory explained? Are there examples?
5. **Test coverage** — are edge cases exercised?

### Responding to review comments

- Address every comment, even if just to say "done" or "I disagree because…".
- Push new commits (do **not** force-push after review starts — it loses context).
- Re-request review once you've addressed all comments.
- If a comment is unclear, ask for clarification in the thread — don't guess.

### Merge policy

- Squash-and-merge is used by default to keep `main` history clean.
- The maintainer writes the final commit message summarising all changes.
- After merge, delete your feature branch (`git push origin --delete feature/your-branch`).

### Timeline

- The maintainer aims to leave a first review within **48 hours** of a PR being marked "Ready for review".
- If you haven't heard back in 3 days, ping the PR with a comment — it may have been missed.

---

## 11. Common Commands Reference

All commands run **inside the container** (VS Code terminal, or `docker compose exec emachines-dev bash`).

```bash
# Start the container (terminal-only workflow)
docker compose up

# Open a shell in the running container
docker compose exec emachines-dev bash

# Export notebooks to Python
nbdev-export

# Run all tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=emachines --cov-report=term-missing

# Run pre-commit on all files
pre-commit run --all-files

# Format code manually
black --line-length 100 emachines/ tests/
isort --profile black --line-length 100 emachines/ tests/

# Type check
mypy emachines/ --ignore-missing-imports

# Start JupyterLab (then open http://localhost:8888)
jupyter lab --ip=0.0.0.0 --allow-root --no-browser

# Rebuild the Docker image (after Dockerfile changes)
docker compose up --build

# Stop the container
docker compose down
```

---

## 12. Getting Help

| Channel | Use for |
|---------|---------|
| [GitHub Discussions](https://github.com/NaveenDeepak/emachines/discussions) | Questions, ideas, "how do I…" |
| [GitHub Issues](https://github.com/NaveenDeepak/emachines/issues) | Bug reports, confirmed feature requests |
| PR comments | Code-specific feedback during review |

When filing a bug, always include: OS, Docker version, Python version, and the full error traceback. The issue template will prompt you.

---

*Last updated: May 2026 · Maintained by [@NaveenDeepak](https://github.com/NaveenDeepak)*
