FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df AS builder
WORKDIR /build
COPY requirements/runtime.txt ./requirements.txt
RUN python -m pip wheel --no-cache-dir --only-binary=:all: --wheel-dir=/wheels -r requirements.txt

FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
COPY requirements/runtime.txt /tmp/requirements.txt
RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    python -m pip install --no-cache-dir --no-index --find-links=/wheels -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt
COPY api ./api
COPY common ./common
COPY db ./db
COPY worker ./worker
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
