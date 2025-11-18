# Example-bot

This is a simple bot project based on the Luxchatbot framework.
It is meant to be an example for other bots to discover some basic uses of the bot.
Everything on this bot is an example, and can be changed if you want to do things differently.

## Docker

This bot can be deployed using docker.
In order to do this, you need to have the luxchatbot and the example-bot folder at the root of the project like it is the case on this repo.

Build the docker image :
```
sudo docker build -t example-bot:latest \
--build-arg http_proxy=my_proxy \
--build-arg https_proxy=my_proxy \
-f ./example-bot.dockerfile ../
```

Run docker container :

```
sudo docker run --rm --name example-bot \
-v ./store:/bot/example-bot/store \
-v ./config.ini:/bot/example-bot/config.ini:ro \
  example-bot:latest
```