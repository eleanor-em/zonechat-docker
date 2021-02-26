FROM python:3.9-slim as base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y gcc libffi-dev g++
WORKDIR /app

FROM base as builder

COPY poetry.lock pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir "poetry==1.1.4" \
 && poetry config virtualenvs.create false \
 && poetry install --no-dev \
 && pip uninstall --yes poetry

COPY ./main.py ./
COPY docker-entrypoint.sh ./

CMD ["sh", "-c", "./docker-entrypoint.sh"]
