ARG PYTHON_VERSION
ARG PREFECT_VERSION
FROM prefecthq/prefect:${PREFECT_VERSION}-python${PYTHON_VERSION}

ENV PATH=/root/.local/bin:$PATH

SHELL ["/bin/bash", "-c"]
RUN apt update && \
    apt install -y curl wget gpg lsb-release && \
    wget -qO - 'https://proget.makedeb.org/debian-feeds/prebuilt-mpr.pub' | gpg --dearmor | tee /usr/share/keyrings/prebuilt-mpr-archive-keyring.gpg 1> /dev/null && \
    echo "deb [arch=all,$(dpkg --print-architecture) signed-by=/usr/share/keyrings/prebuilt-mpr-archive-keyring.gpg] https://proget.makedeb.org prebuilt-mpr $(lsb_release -cs)" | tee /etc/apt/sources.list.d/prebuilt-mpr.list && \
    apt update && \
    apt install -y just && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    apt clean && apt autoremove -y && \
    rm -rf /var/lib/apt/lists/*

ENV PATH=/root/.local/bin:$PATH

COPY poetry.lock poetry.lock
COPY pyproject.toml pyproject.toml
COPY justfile justfile
RUN poetry config virtualenvs.create false
RUN poetry install --only main