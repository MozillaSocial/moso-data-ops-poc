ARG PYTHON_VERSION
ARG PREFECT_VERSION
FROM prefecthq/prefect:${PREFECT_VERSION}-python${PYTHON_VERSION}

ENV PATH=/root/.local/bin:$PATH

RUN apt update && \
    apt install -y curl default-libmysqlclient-dev \
    pkg-config \
    gcc && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    apt clean && apt autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY poetry.lock poetry.lock
COPY pyproject.toml pyproject.toml
RUN poetry config virtualenvs.create false
RUN poetry install --only main