# Deploy with docker

## Dockerfile structure

You can build the your bot's docker image like the following, only replacing "your-bot" with your bot name.

```Dockerfile
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

COPY ./your-bot /bot/your-bot

#Run the app without the build deps
FROM python:3.13-alpine

WORKDIR /bot

COPY --from=builder /bot/. /bot/.
ENV PATH="/bot/.venv/bin:$PATH"

CMD ["python3", "your-bot/"]
```

### With custom libs

Sometimes, the default python librairies included in the luxchatbot project won't be able to fit your needs.

To solve this issue, you can add those libraries in a requirements.txt file and install them in the builder with the main dependencies.

Here is an example with the library psycopg[c] (rebuild psycopg from c code).

```Dockerfile
FROM python:3.13-alpine AS builder

#Install build dependencies
RUN apk update
RUN apk add build-base

#These two packages are needed to build psycopg
RUN apk add libpq-dev
RUN apk add python3-dev

WORKDIR /bot

COPY ./luxchatbot /bot/luxchatbot

#Create venv and install/build python libs
RUN python3 -m venv .venv
ENV PATH="/bot/.venv/bin:$PATH"
RUN pip install --no-cache-dir -e luxchatbot

COPY ./your-bot /bot/your-bot

#Install custom python libraries
RUN pip install -r /bot/your-bot/requirements.txt

#Run the app without the build deps
FROM python:3.13-alpine

#Install libpq prod for psycopg lib (needed at runtime)
RUN apk update
RUN apk add libpq

WORKDIR /bot

COPY --from=builder /bot/. /bot/.
ENV PATH="/bot/.venv/bin:$PATH"

CMD ["python3", "your-bot/"]
```

As you can see, it gets a bit more complex, but it's not too hard when you understand what was changed from the previous verison.

From the previous verison we :
- Installed new dev packages in the builder to be able to build the libraries from c code
- Added a line to install the python libraries in your requirements.txt file
- Install a package needed for our lib to run in the last stage

In short, we simply install the packages and libs you need in the builder, and keep only what's absolutely necessary in the last stage of the dockerfile.

Your example might not need additional packages, and simply pure python libs, in which cas you can simply take the first dockerfile example and add the following line in the builder, after copying the files of your bot.
```Dockerfile
RUN pip install -r /bot/your-bot/requirements.txt
```

## Build the image

Run this command from the root of the luxchatbot project
```bash
docker build -t your-bot:version -f your-bot.dockerfile .
```

Or with proxies
```bash
docker build -t your-bot:version -f ./your-bot/your-bot.dockerfile \
    --build-arg http_proxy=http://proxy.local:proxy_port \
    --build-arg https_proxy=https://proxy.local:proxy_port \
    .
```

## Run the bot

To run the bot, you can use the following command.
```bash
sudo docker run --rm --name your-bot \
    -v ./your-bot/store:/bot/your-bot/store \
    -v ./your-bot/config.ini:/bot/your-bot/config.ini:ro \
    your-bot:version
```

Or with custom logging config :
```bash
sudo docker run --rm --name your-bot \
    -v ./your-bot/store:/bot/your-bot/store \
    -v ./your-bot/config.ini:/bot/your-bot/config.ini:ro \
    -v ./your-bot/logging.ini:/bot/your-bot/logging.ini:ro \
    your-bot:version
```