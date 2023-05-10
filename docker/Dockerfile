FROM python:3.10-slim

# Locale.
ENV LANG en_US.utf8
RUN apt-get update -y && apt-get install -y locales alien && \
    localedef -i en_US -c -f UTF-8 -A \/usr/share/locale/locale.alias en_US.UTF-8

# Environment.
WORKDIR /app
COPY ./poetry.lock ./
COPY ./pyproject.toml ./
RUN pip install --no-cache-dir --upgrade --root-user-action ignore pip setuptools wheel poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

# App.
COPY ./src ./src
RUN poetry install
