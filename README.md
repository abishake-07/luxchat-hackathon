# Luxchat Hackaton

## Table of content

- [Requirements](#requirements)
- [Your project](#your-project)
- [Expected](#expected)
- [Getting started](#getting-started)
- [Project types](#project-types)
    - [Local setup (Client or server feature)](#local-setup-client-or-server-feature)
        - [Create a user](#create-a-user)
        - [Edit the client](#edit-the-client)
        - [Edit the server](#edit-the-server)
    - [Custom bot](#custom-bot)
        - [Quickstart](#quickstart)
        - [Running the example-bot](#running-the-example-bot)
            - [On a local synapse server](#on-a-local-synapse-server)
            - [On the hackaton synapse server](#on-the-hackaton-synapse-server)
        - [Customize the bot](#customize-the-bot)
        - [Dos and donts](#dos-and-donts)
        - [More info](#more-info)

## Requirements

Nothing is absolutely required as most of this readme is about how to setup your environment easily.

However, we advise you to have :
- a linux machine or VM (Ideally based on debian)
- docker installed
- git installed

## Your project

This section is dedicated to describing your project.
You can write a short description of your project, and fill the following table with what parts of the app your worked on (simply add an X under the parts your worked on).


| Luxchat (Webclient) | Synapse (server) | Bot |
|---------------------|------------------|-----|
|                     |                  |     |


## Expected

At the end of the hackaton, you must push your last changes to this repo and tag it with "final". Don't forget to fill the [your project](#your-project) section.

You will then have to demo your project in front of the jury.

For that, you need to have at least one machine in your group that runs your project correctly.

## Getting started

To get started with the hackaton, please fork this project and invite your team to work on your fork.

You can start working right away after reading what's [expected](#expected) at the end of the hackaton.
However, if you wish to have a little more indications on how to start your project, you are advised to read the rest of this readme.

The first steps are to complete whatever your project may be :
Clone this project (or your fork) :
```
git clone https://framagit.org/lxcode/luxchat-hackaton
```

Go into the working dir :
```
cd luxchat-hackaton
```

From there, you will need to take different steps depending on your project :
- [Custom bot](#custom-bot)
- [Client feature](#local-setup-client-or-server-feature)
- [Server feature](#local-setup-client-or-server-feature)
- [Android or IOS feature](#android-or-ios-feature)

## Project types

### Android or IOS feature

If you want to work on the android or IOS apps, you can find the code from these repos :
- https://repo.luxchat4gov.lu/src-ios/
- https://repo.luxchat4gov.lu/src-android/

### Local setup (Client or server feature)

Make sure you are located in the root of this project (either forked or directly cloned).

Setup your local environment :
```bash
sudo sh scripts/setup.sh
```

Run the dockerfile :
```bash
docker compose up -d
```

This will start you a full local setup with a synapse server and a luxchat webclient.

Go to the server url and trust the certificate:
```
https://local.synapse.server/_matrix/static
```

You will find a page warning you about the self-trusted certificate, simply click advanced and accept to trust it on your browser (the steps depend on the browser).

Connect to your webclient and trust the certificate too:
```
https://local.synapse.server:8080/
```

You should be redirected to your local luxchat's login page.

You should have 2 options on your dropdownList, LOCAL and HACKATON.
Local is your local instance of Synapse, so you will use this server if you want to work on server features.
Otherwise, you can work on the HACKATON server that is a remote instance set up for the occasion.

It may take a little when trying to switch the server when your select another option in the dropdown list.

Tips : If working on a Virtualbox VM, you can use the "shared folder" option to be able to update your code automatically on your vm.

#### Create a user

First, let's create a user so that you can connect to your local luxchat once you finish setting up.

```
sudo docker exec -it synapse register_new_matrix_user -u admin -p admin -a -c /data/homeserver.yaml http://localhost:8008
```

#### Edit the client

Now that you have a client running, you would maybe like to know how to edit the client.

To edit the client, you can edit anything in the element-web folder, this is the source code that will be built.

The only exceptions are:
- The element-web/src/SdkConfig.ts located in the luxchat-config/SdkConfig.ts
- The element-web/deltas/strings located in the luxchat-config/translations

So if you want to change your translations or the SdkConfig, work on those instead, or edit the custom-luxchat.dockefile.

To rebuild after doing some. changes :
```
docker build -t custom-luxchat:latest -f custom-luxchat.dockerfile .
```

Make sure you restart your docker compose after each rebuild.

#### Edit the server

You should have a copy of the source code with the built rust sdk in the custom_synapse folder, you can edit it from this folder.

When doing changes, you don't need to rebuild the image, simply restart your docker compose.


### Custom bot

Please make sure you are located in the root of this project (either forked or directly cloned).

#### Quickstart

Download the tar of the framework :
```bash
sudo sh scripts/setup-bot.sh
```
You should now have a "bot" folder 

In this folder, you should find two folders :
- luxchatbot : the framework for the bot
- example-bot : an example bot made for demoing what the framework can do.

First, we'll try to run the example-bot, to understand how to configure and run a bot.

#### Running the example-bot

All bots are configured using a [config.ini file](https://framagit.org/lxcode/luxchatbot#configuration) that contains various information such as the bot's access token, device id, matrix id, etc.

Those are the configs required for an example-bot.

Copy the config.ini.sample:
```bash
cp bot/example-bot/config.ini.sample bot/config.ini
```

Now we'll configure the bot depending on what homeserver you want it to run on.

##### On a local synapse server.

If you want to run your bot locally, please follow the [local setup step](#local-setup-client-or-server-feature) and come back to this part after you created a user and successfully connected to it on the webclient.

Run your local setup :
```bash
docker compose up -d
```

Now, we'll create a user for your bot :
```bash
sudo docker exec -it synapse register_new_matrix_user -u bot -p bot -c /data/homeserver.yaml http://localhost:8008
```

You can create a token/device_id pair with this curl command :
```bash
curl --location 'https://local.synapse.server/_matrix/client/r0/login' \
	--header 'XCustomUserAgent: luxchat4all' \
	--data '
{
    "identifier": {
        "type": "m.id.user",
        "user": "bot"
    },
    "password": "bot",
    "type": "m.login.password"
}'
```

Expected result :
```json
{
    "user_id":"@bot:local.synapse.server",
    "access_token":"an_access_token",
    "home_server":"local.synapse.server",
    "device_id":"XULFXSUQHH"
}
```

You can pick all those information and put them in your example-bot's config.ini to fill your homeserver section.

You will then need to connect on the server using a webclient, using another account than the bot (e.g. the admin account you should have created during the [local setup](#local-setup-client-or-server-feature)).

Create a room and click on the ... -> settings -> advanced.
Copy the room id and save it somewhere.

Invite the bot in the room (paste this id in the invite field : @bot:local.synapse.server ).

You can then go back to your config file to fill it like the following :

```ini
[homeserver]
homeserver = local.synapse.server
bot_uid = @bot:local.synapse.server
access_token = youraccesstokenhere
device_id = yourdeviceIDhere

[config]
owner_id = @admin:local.synapse.server
management_room = !yourroomid:local.synapse.server
bot_name = Example Bot
command_prefix = !
proxy =
start_looper = True

[api]
api_enabled = True
api_host = 0.0.0.0
api_port = 5013
api_workers = 3
auth_required = True
api_password = mysecret

[openweatherapi]
api_key = not_required_here
```

Simply replace the management_room and homeserver section if it's not done.

OPTIONAL : If you want to test the "meteo" command, create an account on https://openweathermap.org/ and put the api_key in the openweatherapi.api_key field.

You can now build your bot's docker image :
```bash
docker build -t custom-bot:latest -f bot/example-bot/example-bot.dockerfile ./bot
```

The first build takes a lot of time, but it should be shorter in the future.

Finally, uncomment this block in your docker-compose.yml:
```docker
custom-bot:
    container_name: custom-bot
    image: custom-bot:latest
    depends_on:
      synapse:
        condition: service_started
    ports:
      - 5013:5013
    volumes:
      - ${WORKDIR}/bot/etc_hosts:/etc/hosts:ro
      - /etc/ssl/certs/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt:ro
      - ${WORKDIR}/bot/config.ini:/bot/example-bot/config.ini
      - ${WORKDIR}/bot/store:/bot/example-bot/store
    networks:
      luxchat-network:
        ipv4_address: 172.20.0.5
```

restart your setup :
```
docker compose down
docker compose up -d
```

Connect to your account, go to the room you created for the bot, and type "!hello bot"

You should have a response from the bot saying : "Hello, you said : bot"

If your bot's messages have a red shield, don't worry, you can safely ignore it.

You can now move on to [customizing the bot](#customize-the-bot).

##### On the hackaton synapse server

You will need the bot information you should have been provided with, if you don't have any bot information, please ask an organizer.

You should have :
- The matrix ID of your bot
- A JWT token for your bot

Set your JWT variable 
```bash
botJWT=<your_bot_jwt>
```

Now generate the bot's access_token and device_id :
```bash
curl --location 'https://poc.luxchat4pro.lu/_matrix/client/r0/login'\
    --header 'XCustomUserAgent: luxchat4all'\
    --data "{\"type\":\"org.matrix.login.jwt\", \"token\": \"${botJWT}\"}"
```

Expected result :
```json
{
    "user_id":"@yourbot:poc.luxchat4pro.lu",
    "access_token":"an_access_token",
    "home_server":"poc.luxchat4pro.lu",
    "device_id":"XULFXSUQHH"
}
```

Take all those info and fill out this config.ini and save it to bot/config.ini :
```ini
[homeserver]
homeserver = poc.luxchat4pro.lu
bot_uid = your_bot_id_here
access_token = youraccesstokenhere
device_id = yourdeviceIDhere

[config]
owner_id = your_user_id_here
management_room = !yourroomid:poc.luxchat4pro.lu
bot_name = Example Bot
command_prefix = !
proxy =
start_looper = True

[api]
api_enabled = True
api_host = 0.0.0.0
api_port = 5013
api_workers = 3
auth_required = True
api_password = mysecret

[openweatherapi]
api_key = not_required_here
```

OPTIONAL : If you want to test the "meteo" command, create an account on https://openweathermap.org/ and put the api_key in the openweatherapi.api_key field.

Now, it's time to run the bot

Build the image
```bash
docker build -t custom-bot:latest -f bot/example-bot/example-bot.dockerfile ./bot
```

Run the bot
```bash
docker run -it --rm \
    -v bot/config.ini:/bot/example-bot/config.ini \
    -v bot/store:/bot/example-bot/store \
    custom-bot
```

Connect to your account, go to the room you created for the bot, and type "!hello bot"

You should have a response from the bot saying : "Hello, you said : bot"

If your bot's messages have a red shield, don't worry, you can safely ignore it.

You can now move on to [customizing the bot](#customize-the-bot).

#### Customize the bot

You can now rename the example-bot folder to whatever name you want to give your bot, edit your docker-compose.yml or your docker command and start to work on the code.

To rebuild your bot's image after your changes :
```bash
docker build -t custom-bot:latest -f bot/example-bot/example-bot.dockerfile ./bot
```

You don't have to change the store or config.ini location or name, and should be able to keep the same config.ini connection information, although you may need to change other config elements such as the display name or remove the openweatherapi section.

#### Dos and donts

- Don't mix access_tokens and device_ids (e.g. using an access token with a device id generated for another access toekn), they are linked and shouldn't be mixed.
- Don't use the same access_token/device_id pair for multiple instances of the bot (get one pair for each member of the team, otherwise cryptography will not work and your bot won't be able to interact with the server).

#### More info

For more info on how to build, run, or edit a custom bot, you can find documentation in [the framework's readme](https://framagit.org/lxcode/luxchatbot/-/blob/main/README.md?ref_type=heads).