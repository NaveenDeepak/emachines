# Contributing to emachines

Thank you for contributing! This document covers everything you need: environment setup, the notebook-driven development workflow, and how to get your work merged.

---

## Table of Contents

1. [How the Library Works](#1-how-the-library-works)
2. [Toolchain — What You Need](#2-toolchain--what-you-need)
3. [Setting Up Your Environment](#3-setting-up-your-environment)
4. [Contributor Workflow (step by step)](#4-contributor-workflow-step-by-step)
5. [Notebook Standards](#5-notebook-standards)
6. [Running Tests and Export Locally](#6-running-tests-and-export-locally)
7. [Branch and Commit Conventions](#7-branch-and-commit-conventions)
8. [Opening a Pull Request](#8-opening-a-pull-request)
9. [Review and Merge Process](#9-review-and-merge-process)
10. [Common Commands Reference](#10-common-commands-reference)

---

## 1. How the Library Works

emachines uses **[nbdev](https://nbdev.fast.ai/)** — a notebook-driven development system.

```
nbs/XX_module.ipynb   ──nbdev-export──►   emachines/XX/module.py
        │                                          │
   theory + code                           importable library
   + examples                              (auto-generated,
   + tests                                  do not edit directly)
```

**The rule:** You write notebooks. nbdev generates the Python library. Never edit the files inside `emachines/` by hand — they will be overwritten on the next export.

---

## 2. Toolchain — What You Need

| Tool | Purpose | Install |
|------|---------|---------|
| **Python ≥ 3.10** | Runtime | [python.org](https://www.python.org/) |
| **Git ≥ 2.39** | Version control | [git-scm.com](https://git-scm.com/) |
| **JupyterLab** | Edit notebooks | installed via dev dependencies |
| **nbdev ≥ 3.0** | Export + test | installed via dev dependencies |

Verify your setup:
```bash
python --version   # 3.10 or higher
git --version
```

---

## 3. Setting Up Your Environment

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/<your-username>/emachines.git
cd emachines

# 2. Add upstream remote
git remote add upstream https://github.com/NaveenDeepak/emachines.git

# 3. Install the project with dev dependencies
pip install -e ".[dev]"
pip install "nbdev>=3.0.0" "jupyterlab>=4.0.0"

# 4. Install pre-commit hooks
pip install pre-commit
pre-commit install

# 5. Verify everything works
nbdev-test --do_print
```

---

## 4. Contributor Workflow (step by step)

### Step 1 — Create a branch

```bash
git checkout main
git pull upstream main
git checkout -b feat/your-module-name
```

### Step 2 — Copy the template notebook

```bash
cp nbs/00_template.ipynb nbs/XX_your_module_name.ipynb
```

Use the next available number prefix (e.g. if the last notebook is `04_results.ipynb`, use `05_`).

### Step 3 — Open JupyterLab and write your notebook

```bash
jupyter lab
```

Open your new notebook and fill in every required section (see [Notebook Standards](#5-notebook-standards) below). Write theory, implementation, examples, and tests all in the same notebook.

### Step 4 — Export the notebook to Python

```bash
nbdev-export
```

This generates (or updates) the Python module in `emachines/`. Verify the output looks correct:

```bash
python -c "from emachines.your_module import your_function; print('✓ import OK')"
```

### Step 5 — Run the tests

```bash
nbdev-test --do_print --timing
```

All test cells (`#| hide` cells containing `assert`) must pass before pushing.

### Step 6 — Commit and push

```bash
git add nbs/XX_your_module.ipynb emachines/your_module/
git commit -m "feat: add XX_your_module — brief description"
git push origin feat/your-module-name
```

The pre-commit hook (`nbdev_clean`) will automatically strip notebook outputs before committing, keeping diffs readable.

### Step 7 — Open a Pull Request

Go to GitHub and open a PR from your branch into `main`. CI will run automatically:

| Check | What it does |
|-------|-------------|
| **Notebook Export Check** | Verifies your notebooks and `.py` files are in sync |
| **Notebook Tests (3.10, 3.11)** | Runs all `#| hide` test cells |
| **Type Check (mypy)** | Type-checks the generated `emachines/` package |

All three must be green before your PR can be reviewed.

---

## 5. Notebook Standards

Every notebook must follow the template in `nbs/00_template.ipynb`. The required sections are:

### Required sections (in order)

| Section | Purpose |
|---------|---------|
| **nbdev YAML header** | `#\| default_exp` directive telling nbdev where to export |
| **Overview** | What the module computes and why it matters |
| **Inputs and Outputs** | Parameter table with symbols, units, ranges |
| **Connections** | Which notebooks feed in, which consume output |
| **Notation** | Symbol table for all math used |
| **Theory + Implementation** *(repeat)* | Each function: equation first, then code, then example |
| **References** | Citation for every equation |
| **Tests** | `#\| hide` cells with assertions for every exported function |

### Key rules

- **Theory lives next to code** — equations immediately before the function that implements them
- **Every `#| export` function** needs a docstring with Parameters, Returns, and a doctest example
- **Every exported function** needs at least one `assert` in the Tests section
- **File naming**: `XX_descriptive_name.ipynb` where `XX` is the next available number prefix
- **Never edit `emachines/` directly** — always edit the notebook and re-run `nbdev-export`

### nbdev directives

| Directive | Where to use it |
|-----------|----------------|
| `#\| default_exp module_name` | First code cell — sets the output module |
| `#\| export` | Any function/class to include in the library |
| `#\| hide` | Test cells — run by nbdev-test, excluded from docs |
| `#\| eval: false` | Skip a cell during nbdev-test (e.g. slow or interactive) |

---

## 6. Running Tests and Export Locally

```bash
# Export notebooks → Python modules
nbdev-export

# Run all notebook tests
nbdev-test --do_print --timing

# Check for drift (same check CI runs)
git diff --exit-code emachines/

# Type check
mypy emachines/ --ignore-missing-imports
```

---

## 7. Branch and Commit Conventions

**Branch names:**
```
feat/description      # new module or feature
fix/description       # bug fix
refactor/description  # restructuring without behaviour change
docs/description      # documentation only
```

**Commit messages** follow [Conventional Commits](https://www.conventionalcommits.org/):
```
feat: add thermal model for PMSM rotor losses
fix: correct iron loss Bertotti coefficient sign
refactor: split magnetics notebook into focused files
docs: add references to winding factor derivation
```

---

## 8. Opening a Pull Request

1. Push your branch and open a PR on GitHub targeting `main`
2. Fill in the PR description:
   - What module/function does this add or fix?
   - What reference (paper/textbook) is the implementation based on?
   - How was it validated? (e.g. "matches emetor.com reference values")
3. Wait for CI — all three checks must be green
4. Request a review or tag the maintainer

---

## 9. Review and Merge Process

- PRs require **at least 1 approving review** before merging
- The reviewer will check: theory correctness, test coverage, docstring quality, and reference citations
- Once approved and CI is green, the maintainer will merge

---

## 10. Common Commands Reference

```bash
# Start working
git checkout main && git pull upstream main
git checkout -b feat/your-feature

# Daily development loop
jupyter lab                          # edit notebooks
nbdev-export                         # generate Python
nbdev-test --do_print                # run tests

# Before pushing
git diff --exit-code emachines/      # check no drift
git add nbs/ emachines/
git commit -m "feat: ..."
git push origin feat/your-feature

# Sync with upstream
git fetch upstream
git rebase upstream/main
```

---

## Getting Help

- Open a [Discussion](https://github.com/NaveenDeepak/emachines/discussions) for questions before filing an issue
- For bugs, open an [Issue](https://github.com/NaveenDeepak/emachines/issues) with a minimal reproducible example
- For new module ideas, open an Issue first to discuss scope before writing code
