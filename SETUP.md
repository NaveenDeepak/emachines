# Development Environment Setup with Docker

This guide sets up a **consistent development environment** using Docker. This ensures everyone has the exact same Python version, dependencies, and tools — **regardless of whether they're on macOS, Windows, or Linux**.

## Why Docker?

✅ **Same environment for everyone** - No "works on my machine" problems  
✅ **Cross-platform** - Works identically on macOS, Windows, Linux  
✅ **No conflicts** - Dependencies isolated from your system  
✅ **Easy onboarding** - One command to get started  
✅ **Reproducible** - Tests run in same environment as production  

## Prerequisites

You need to have **Docker installed** on your computer:

- **macOS/Windows**: Download [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Linux**: `sudo apt-get install docker.io` or equivalent for your distro
- **Verify installation**: Run `docker --version` in terminal

## Quick Start (One Command!)

```bash
# 1. Clone the repository
git clone https://github.com/NaveenDeepak/emachines.git
cd emachines

# 2. Start the development environment
docker-compose up

# 3. Open JupyterLab in your browser
# Navigate to: http://localhost:8888
# (The token/password will be shown in the terminal)
```

**That's it!** You're now in the same environment as everyone else. ✨

## What's Included in the Container?

The Docker container includes everything pre-installed:

- ✓ Python 3.10 (consistent across all machines)
- ✓ nbdev (for notebook-driven development)
- ✓ JupyterLab (for interactive development)
- ✓ All project dependencies (numpy, scipy, pandas, etc.)
- ✓ Development tools (pytest, black, pylint, flake8, mypy)
- ✓ Pre-commit hooks (for code quality)
- ✓ Git (for version control)

## Common Commands

### Start Development (JupyterLab)

```bash
docker-compose up
```

Then open: `http://localhost:8888`

### Open a Terminal in the Container

```bash
docker-compose exec emachines-dev bash
```

Now you can run commands inside the container:
```bash
pytest tests/                    # Run tests
nbdev-export                  # Build library from notebooks
python -m emachines.module_name  # Run code
```

### Stop the Container

```bash
# In another terminal:
docker-compose down
```

Or press `Ctrl+C` in the terminal running `docker-compose up`

### Rebuild the Container (after dependency changes)

```bash
docker-compose up --build
```

## Development Workflow

### 1. Start the Container

```bash
cd /path/to/emachines
docker-compose up
```

### 2. Open JupyterLab

Navigate to `http://localhost:8888` in your browser

### 3. Create/Edit Notebooks

- Navigate to `nbs/` folder in JupyterLab
- Create or edit `.ipynb` files
- Write code and documentation together
- Tests are embedded in notebooks

### 4. Build Python Modules from Notebooks

In the JupyterLab terminal or container bash:

```bash
nbdev-export
```

This exports your notebook code to `/emachines/` Python modules.

### 5. Run Tests

```bash
pytest tests/
```

Or inside a notebook cell:

```python
import pytest
pytest.main(['tests/', '-v'])
```

### 6. Commit Your Changes

```bash
git add nbs/
git add emachines/
git commit -m "Add feature: [description]"
git push
```

## nbdev Workflow in Docker

nbdev is perfectly designed for this:

1. **Develop in notebooks** (`nbs/*.ipynb`)
   - Code + documentation together
   - Easy to explain logic and reasoning
   - Embedded tests and examples

2. **Export to Python** (automatic or manual)
   ```bash
   nbdev-export  # Exports to /emachines/
   ```

3. **Tests run** (both in notebooks and pytest)
   - Tests in notebooks are extracted automatically
   - Or use separate test files in `/tests/`

4. **Documentation generated** automatically from notebooks

## File Structure for nbdev

```
emachines/
├── nbs/                    # 📓 Notebook-driven development
│   ├── 00_core.ipynb       # Core functionality
│   ├── 01_utilities.ipynb  # Utilities
│   └── index.ipynb         # Documentation index
├── emachines/              # 🐍 Auto-generated Python files
│   ├── __init__.py
│   ├── core.py            # Generated from 00_core.ipynb
│   └── utilities.py       # Generated from 01_utilities.ipynb
├── tests/                 # 🧪 Test files
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Troubleshooting

### Docker won't start

```bash
# Check if Docker is running
docker ps

# If not, start Docker Desktop or Docker daemon
# macOS/Windows: Open Docker Desktop app
# Linux: sudo service docker start
```

### Can't access JupyterLab

- Ensure `docker-compose up` shows "Jupyter Server is running"
- Try: `http://localhost:8888`
- Check the token in terminal output
- Try clearing browser cache or using incognito mode

### Port 8888 already in use

Edit `docker-compose.yml` and change port mapping:

```yaml
ports:
  - "8889:8888"  # Use port 8889 instead
```

Then access: `http://localhost:8889`

### Permission denied errors

```bash
# On Linux, you might need:
sudo chmod 666 /var/run/docker.sock
# or add your user to docker group:
sudo usermod -aG docker $USER
```

### Changes to notebooks aren't showing

```bash
# Rebuild the library
docker compose exec emachines-dev nbdev-export

# Or restart the container
docker-compose restart
```

## Environment Consistency Checklist

Before starting development:

- [ ] Docker is installed (`docker --version`)
- [ ] Container is running (`docker-compose up` shows no errors)
- [ ] JupyterLab is accessible (`http://localhost:8888`)
- [ ] You can open/create notebooks
- [ ] Tests run without errors (`pytest tests/`)

## Developing on Different OS

The beauty of Docker is that this setup works **exactly the same** on:

- ✅ macOS (Intel & Apple Silicon)
- ✅ Windows (with WSL2 or Docker Desktop)
- ✅ Linux (any distribution)

No special instructions needed!

## Questions?

If you have issues:

1. Check this guide again
2. Run `docker logs emachines-dev` to see container logs
3. Open a GitHub Issue with:
   - Your OS (macOS/Windows/Linux)
   - Docker version (`docker --version`)
   - Error message
4. Ask in project Discussions

---

**You're all set!** Start with:

```bash
docker-compose up
```

Then open `http://localhost:8888` and begin developing in notebooks! 🚀

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full contribution workflow.
