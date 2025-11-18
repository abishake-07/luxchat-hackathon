FROM python:3.13-alpine AS builder

#Install build dependencies
RUN apk update
RUN apk add build-base

WORKDIR /bot

COPY ./luxchatbot /bot/luxchatbot

#Create venv and install/build python libs
RUN python3 -m venv .venv
ENV PATH="/bot/.venv/bin:$PATH"
RUN pip install --no-cache-dir -e luxchatbot

COPY ./example-bot /bot/example-bot

#Run the app without the build deps
FROM python:3.13-alpine

WORKDIR /bot

COPY --from=builder /bot/. /bot/.
ENV PATH="/bot/.venv/bin:$PATH"

CMD ["python3", "example-bot/"]