
FROM python:3.11-slim

RUN apt update && apt upgrade -y 

WORKDIR /var/task

ENV APP_NAME="MOTIVE PARTNERS POC" \
    APP_DESCRIPTION="MOTIVE PARTNERS POC" \
    APP_VERSION=0.0.1 \
    APP_ENCODING_ALG=HS256 \
    APP_JWT_ENABLED=False \
    APP_LOG_NAME=motive.log \
    PREFERRED_URL_SCHEME=https \
    SESSION_PERMANENT=True \
    PERMANENT_SESSION_LIFETIME=60 \
    TESTING=False \
    CSRF_ENABLED=True \
    DEBUG=True \
    DEFAULT_LANGUAGE=en_US \
    ITEMS_PER_PAGE=20 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RUNNING_OS=Type1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

COPY requirements/requirements.in requirements/
RUN pip install pip-tools \
    && pip-compile requirements/requirements.in --verbose \
    && pip install --no-cache-dir -r requirements/requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /root/.cache/pip


COPY . /var/task

ENV PYTHONPATH="/var/task:${PYTHONPATH}"

CMD ["uvicorn", "application:app", "--host", "0.0.0.0", "--port", "8081", "--reload"]

