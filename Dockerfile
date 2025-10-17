###########
# BUILDER #
###########
FROM python:3.11.11-slim-bullseye AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc git

RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


#########
# FINAL #
#########
FROM python:3.11.11-slim-bullseye

RUN addgroup --system app && adduser --system --group app

ENV HOME=/app
ENV APP_HOME=/app
ENV PYTHONPATH="${PYTHONPATH}:/app/feedbackbot"
WORKDIR /app

RUN apt-get update && apt-get update -y && apt-get install -y --no-install-recommends netcat
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache /wheels/*

COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# copy project
COPY ./feedbackbot $APP_HOME/feedbackbot
RUN chown -R app:app $APP_HOME

USER app

ENTRYPOINT ["/app/entrypoint.sh"]