workdir=$(pwd)

echo "WORKDIR=${workdir}" > .env

# Generate synapse config
docker image pull matrixdotorg/synapse:latest

docker run -it --rm \
    -v ${workdir}/synapse-data:/data \
    -e SYNAPSE_SERVER_NAME=local.synapse.server \
    -e SYNAPSE_REPORT_STATS=yes \
    matrixdotorg/synapse:latest generate

rm ${workdir}/synapse-data/homeserver.yaml
cp ${workdir}/synapse-config/homeserver.yaml ${workdir}/synapse-data/homeserver.yaml


# Add server domain to /etc/hosts
echo "127.0.0.1 local.synapse.server" >> /etc/hosts

# Generate openssl certificate for nginx
openssl req -newkey rsa:2048 -keyout ${workdir}/nginx/certs/local.synapse.server.key -x509 -days 365 -nodes -out ${workdir}/nginx/certs/local.synapse.server.crt -subj "/CN=local.synapse.server"

cp ${workdir}/nginx/certs/local.synapse.server.crt /usr/local/share/ca-certificates/local.synapse.server.crt

update-ca-certificates

# Client Setup

curl https://repo.luxchat4gov.lu/src-web-fat/luxchat-web-20251029T093428.tar.gz --output luxchat.tar.gz

tar -xzvf luxchat.tar.gz
tar -zxvf matrix-js-sdk.tar.gz

docker build -t custom-luxchat:latest -f custom-luxchat.dockerfile .


# Server setup

docker image pull python:3.13

git clone https://github.com/element-hq/synapse

cd synapse && git checkout v1.120.2 && cd ${workdir}

docker build -t custom-synapse:latest -f ${workdir}/custom-synapse.dockerfile .

#Copy built rust libraries to local machine
if [ ! -d "${workdir}/custom_synapse" ]; then

    docker create --name temp_container custom-synapse
    docker cp temp_container:/synapse/synapse ${workdir}/custom_synapse
    docker rm temp_container
fi
