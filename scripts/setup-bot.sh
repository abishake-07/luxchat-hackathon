workdir=$(pwd)

docker image pull python:3.13-alpine

curl https://framagit.org/lxcode/luxchatbot/-/archive/v1.11.0/luxchatbot-v1.11.0.tar.gz -o luxchatbot.tar.gz
tar -xzvf luxchatbot.tar.gz
mv ${workdir}/luxchatbot-v1.11.0 ${workdir}/bot
chmod -R a+rwx ${workdir}/bot
cp ${workdir}/bot/example-bot/logging.ini.sample ${workdir}/bot/example-bot/logging.ini
echo "
127.0.0.1       localhost
172.20.0.4      local.synapse.server

::1     localhost ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
172.18.0.5      0f116de50610
" > ${workdir}/bot/etc_hosts