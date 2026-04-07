FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc libpq-dev git \
        libxcb1 libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Build with:
#   DOCKER_BUILDKIT=1 docker build \
#     --secret id=pip_extra_index,env=PIP_EXTRA_INDEX_URL \
#     -t tone .
# where PIP_EXTRA_INDEX_URL points at the Cloudsmith private PyPI for tone-pipecat.
RUN --mount=type=secret,id=pip_extra_index \
    PIP_EXTRA_INDEX_URL="$(cat /run/secrets/pip_extra_index 2>/dev/null || true)" \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
