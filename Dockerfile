FROM python:3.13-slim   

RUN mkdir -p /code

WORKDIR /code

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT="/venv"
ENV UV_COMPILE_BYTECODE=1
ENV PATH="$UV_PROJECT_ENVIRONMENT/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

CMD alembic upgrade head && python /code/main.py
