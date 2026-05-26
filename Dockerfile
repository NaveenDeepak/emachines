# Development environment for emachines
# Ensures consistent environment across macOS, Windows, and Linux
# Python 3.10 with nbdev, Jupyter, and all dependencies

FROM python:3.10-slim

# Set working directory
WORKDIR /workspace

# Explicitly put pip's script directory on PATH for all shell types
# (interactive, non-interactive, login, and docker exec)
ENV PATH="/usr/local/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first (separate layer — rarely changes)
RUN pip install --upgrade pip setuptools wheel

# Install nbdev and dev tools BEFORE copying project files
# so this expensive layer is cached independently of code changes
RUN pip install \
    nbdev>=2.3.0 \
    jupyterlab>=4.0.0 \
    black>=23.7.0 \
    isort>=5.12.0 \
    pylint>=2.17.0 \
    flake8>=6.0.0 \
    mypy>=1.4.0 \
    pre-commit>=3.3.0

# Copy project files (after installing tools, so code changes don't
# invalidate the expensive pip install layers above)
COPY . /workspace/

# Install the project in development mode
RUN pip install -e ".[dev]"

# Install pre-commit hooks
RUN pre-commit install --install-hooks || true

# Verify key tools are on PATH (fails the build if something is missing)
RUN nbdev-export --help > /dev/null && \
    jupyter --version > /dev/null && \
    black --version > /dev/null && \
    echo "✅ All tools verified on PATH"

# Expose JupyterLab port
EXPOSE 8888

# Set up Jupyter configuration
RUN jupyter notebook --generate-config && \
    echo "c.NotebookApp.ip = '0.0.0.0'" >> ~/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_root = True" >> ~/.jupyter/jupyter_notebook_config.py

# Default command: start JupyterLab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--allow-root", "--no-browser"]
