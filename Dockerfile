FROM python:3.11-slim

WORKDIR /app

# 构建所需最小源：setuptools 需 pyproject.toml + src（package-dir 指向 src/safe_swe_lite）+ examples 包
COPY pyproject.toml ./
COPY src ./src
COPY examples ./examples

RUN pip install --no-cache-dir ".[web]"

EXPOSE 8000

ENTRYPOINT ["safe-swe-lite"]
CMD ["web"]
