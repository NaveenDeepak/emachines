# Local Setup Guide

## Why the Container Exists

emachines is a **notebook-first library**. Every module, every function, every
test lives in a Jupyter notebook under `nbs/`. The Python files inside
`emachines/` are **auto-generated** by nbdev — they are never written by hand
and must never be edited directly.

This has two consequences for local setup:

**1. The container is the environment.** emachines produces physics-validated
numerical results. Motor winding factors, iron loss coefficients, and BH curve
fits are all validated against reference values with tight tolerances. These
results are sensitive to library versions — a different numpy or scipy can
produce subtly different floats that silently break assertions. The Docker
container pins Python 3.10, nbdev, numpy, scipy, and every other dependency
to the exact same versions used in CI. Your local results will match CI results
exactly.

**2. nbdev is not optional.** The library only works correctly if the nbdev
workflow is followed end-to-end:

```
Edit notebook (nbs/)
      │
      ▼
nbdev-export          ← generates emachines/ Python files
      │
      ▼
nbdev-test            ← runs #| hide test cells in each notebook
      │
      ▼
git commit            ← pre-commit runs nbdev_clean to strip outputs
      │
      ▼
CI drift check        ← verifies notebooks and emachines/ are in sync
```

If you skip `nbdev-export` before committing, the CI drift check will fail.
If you edit files in `emachines/` directly, they will be silently overwritten
the next time anyone runs `nbdev-export`. There is no fallback — the workflow
is the contract.

---

## What You Need

| Tool | Minimum version | Install |
|------|----------------|---------|
| **Git** | 2.39 | [git-scm.com](https://git-scm.com/) |
| **Docker Desktop** (macOS/Windows) | any | [docker.com](https://www.docker.com/products/docker-desktop) |
| **Docker Engine + Compose plugin** (Linux) | any | [docs.docker.com/compose/install](https://docs.docker.com/compose/install/) |
| **WSL2** (Windows, optional) | — | Recommended for better filesystem performance: Docker Desktop → Settings → "Use the WSL2 based engine" |

Verify before continuing:
```bash
git --version
docker compose version   # note: no hyphen — Docker Compose V2
```

---

## Option A — Docker (recommended)

### First-time setup

```bash
# 1. Fork on GitHub, then clone your fork
git clone https://github.com/<your-username>/emachines.git
cd emachines
git remote add upstream https://github.com/NaveenDeepak/emachines.git

# 2. Start the container (builds the image on first run — takes 2–3 min)
docker compose up -d

# 3. Verify it's running
docker compose ps
# emachines-dev   running   0.0.0.0:8888->8888/tcp

# 4. Open a shell inside the container
docker compose exec emachines-dev bash

# 5. Inside the container — install pre-commit hooks once
pre-commit install

# 6. Verify the setup
nbdev-export          # should complete with no errors
nbdev-test --do-print # all tests should pass
```

Open JupyterLab at [http://localhost:8888](http://localhost:8888).

If a token is required:
```bash
docker compose logs emachines-dev | grep token
```

> **Port conflict?** Edit `docker-compose.yml` and change `"8888:8888"` to `"8889:8888"`,
> then open [http://localhost:8889](http://localhost:8889).

### Daily Docker commands

```bash
docker compose up -d           # start
docker compose down            # stop
docker compose up --build -d   # rebuild after Dockerfile changes
```

---

## Option B — Direct install

Only use this if you cannot run Docker (e.g. restricted corporate environment).
You are responsible for matching the Python and dependency versions used in CI.
Results may differ from CI if your environment does not match exactly.

```bash
# Python 3.10 required — other versions are not guaranteed to match CI results
python --version   # must be 3.10.x

git clone https://github.com/<your-username>/emachines.git
cd emachines
git remote add upstream https://github.com/NaveenDeepak/emachines.git

pip install -e ".[dev]"
pip install "nbdev>=3.0.0" "jupyterlab>=4.0.0"
pip install pre-commit
pre-commit install

nbdev-export
nbdev-test --do-print
```

---

## Daily Development Loop

Whether using Docker or direct install, the workflow is the same.
All commands run **inside the container shell** if using Docker.

```bash
# 1. Open JupyterLab (skip if using Docker — it's already running)
jupyter lab

# 2. Edit notebooks in nbs/

# 3. Export notebooks → Python modules  ← never skip this step
nbdev-export

# 4. Run tests
nbdev-test --do-print

# 5. Check for drift before committing
git diff --exit-code emachines/

# 6. Commit
git add nbs/ emachines/
git commit -m "feat: ..."   # pre-commit runs nbdev_clean automatically
git push origin feat/your-branch
```

> **Never edit files inside `emachines/` directly.** They are auto-generated
> from the notebooks and will be overwritten on the next `nbdev-export`.

---

## Troubleshooting

**`nbdev-export` reports drift**
You edited `emachines/` directly, or forgot to export before committing. Fix:
```bash
nbdev-export
git add emachines/
git commit --amend --no-edit
```

**`nbdev-test` fails on import**
Your notebook has a `#| default_exp` pointing to a module that doesn't exist yet.
Run `nbdev-export` first.

**Pre-commit blocks your commit**
`nbdev_clean` stripped notebook outputs — this is expected. Just `git add` the
cleaned notebook and commit again:
```bash
git add nbs/
git commit -m "your message"
```

**Docker container won't start**
```bash
docker compose logs emachines-dev
```
On macOS/Windows: make sure Docker Desktop is open. On Linux: `sudo service docker start`.

**Rebuilding the Docker image**
Only needed when `Dockerfile` or dependencies in `pyproject.toml` change:
```bash
docker compose up --build -d
```

---

*See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full contributor workflow, notebook standards, and PR process.*
