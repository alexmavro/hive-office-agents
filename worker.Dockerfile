# worker.Dockerfile — ephemeral sandbox for Queen-directed code execution
#
# This is NOT the Queen gateway image (Dockerfile).
# This image runs inside ephemeral containers spawned by DockerExecTool.
#
# Design goals:
#   - Pre-loaded with common packages so the Queen doesn't always need to pip install
#   - pip/pip3 available so the Queen CAN install more packages when needed
#   - Non-root user (worker) — extra defence in depth
#   - /sandbox is the file exchange dir (mounted by DockerSandbox at runtime)
#   - No entrypoint — the sandbox passes the exact command to run
#
# Build:
#   docker build -f worker.Dockerfile -t hive-worker:latest .
#
# Test smoke:
#   docker run --rm hive-worker:latest python -c "import pandas; print(pandas.__version__)"

FROM python:3.12-slim

# System tools useful inside a worker container
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        wget \
        git \
        jq \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Pre-install common Python packages
# Queen can still pip install more at runtime — these just save round-trips
RUN pip install --no-cache-dir \
    requests \
    httpx \
    pydantic \
    pandas \
    numpy \
    beautifulsoup4 \
    lxml \
    python-dateutil \
    pytz \
    rich \
    tabulate \
    PyYAML \
    python-dotenv

# Create non-root worker user
RUN useradd -m -u 1000 -s /bin/bash worker

# Pre-create user site-packages directory.
# Python's site module only adds USER_SITE to sys.path if the directory exists at startup.
# Without this, pip installs to ~/.local/lib/... but 'import' fails in the same process.
RUN mkdir -p /home/worker/.local/lib/python3.12/site-packages && \
    chown -R worker:worker /home/worker/.local

# Create /sandbox — the file exchange directory
# DockerSandbox mounts a host temp dir here at runtime
RUN mkdir -p /sandbox && chown worker:worker /sandbox

USER worker
WORKDIR /sandbox
