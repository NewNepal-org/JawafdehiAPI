FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --only main --no-root

COPY manage.py ./
COPY config ./config
COPY allegations ./allegations

RUN python manage.py migrate && \
    echo "yes" | python manage.py seed_allegations

EXPOSE 8080

CMD ["python", "manage.py", "runserver", "--noreload", "0.0.0.0:8080"]
