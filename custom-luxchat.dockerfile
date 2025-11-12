# Builder
FROM --platform=$BUILDPLATFORM node:22-bullseye AS builder

WORKDIR /app


COPY ./matrix-js-sdk /app/matrix-js-sdk

RUN cd matrix-js-sdk && \
    yarn install --network-timeout=200000 --pure-lockfile && \
    yarn build && \
    yarn link --global && \
    cd .. && \
    yarn link matrix-js-sdk

COPY ./.env.build /app/.env
COPY ./luxchat-config/config.json config.json

COPY ./element-web/ /app
COPY ./luxchat-config/favicon.ico /app/res/vector-icons/favicon.ico 
COPY ./luxchat-config/translations /app/deltas/strings
COPY ./luxchat-config/merge_translations.py /app/merge_translations.py
COPY ./luxchat-config/SdkConfig.ts /app/src/SdkConfig.ts

#Config changes
RUN sed -i 's/XCUSTOM_USER_AGENT=Luxchat4Gov/$XCUSTOM_USER_AGENT/g' .env && \
  sed -i 's/HOMESERVER_DNS_TOKEN=$HOMESERVER_DNS_TOKEN/$HOMESERVER_DNS_TOKEN_LUXCHAT_UAT/g' .env && \
  sed -i 's/HOMESERVER_DNS_URL=$HOMESERVER_DNS_URL/$HOMESERVER_DNS_URL_LUXCHAT_UAT/g' .env && \
  sed -i 's|Luxchat4Gov|Luxchat|' src/vector/index.html && \
  sed -i 's|Luxchat4Gov Mobile Guide|Luxchat Mobile Guide|' src/vector/mobile_guide/index.html && \
  sed -i 's|https://govchat.blob.core.windows.net/assets/icon.ico|https://luxchat.blob.core.windows.net/assets/icon.ico|' src/vector/mobile_guide/index.html && \
  sed -i 's|Set up Luxchat4Gov on iOS or Android|Set up Luxchat on iOS or Android|' src/vector/mobile_guide/index.html && \
  sed -i 's|https://apps.apple.com/fr/app/luxchat4gov/id6446884035|https://apps.apple.com/fr/app/luxchat/id6451113532|' src/vector/mobile_guide/index.html && \
  sed -i 's|https://play.google.com/store/apps/details?id=lu.etat.ci.luxchat.gov.android\&hl=fr\&gl=US|https://play.google.com/store/apps/details?id=lu.luxchat4gpe.android\&hl=fr\&gl=US|' src/vector/mobile_guide/index.html && \
  sed -i 's|https://govchat.blob.core.windows.net/assets/icon.ico|https://luxchat.blob.core.windows.net/assets/icon.ico|' src/vector/static/incompatible-browser.html && \
  sed -i 's|Luxchat4Gov|Luxchat|' src/vector/static/incompatible-browser.html && \
  sed -i 's|https://apps.apple.com/fr/app/luxchat4gov/id6446884035|https://apps.apple.com/fr/app/luxchat/id6451113532|' src/vector/static/incompatible-browser.html && \
  sed -i 's|https://play.google.com/store/apps/details?id=lu.etat.ci.luxchat.gov.android\&hl=fr\&gl=US|https://play.google.com/store/apps/details?id=lu.luxchat4gpe.android\&hl=fr\&gl=US|' src/vector/static/incompatible-browser.html && \
  sed -i 's|https://govchat.blob.core.windows.net/assets/icon.ico|https://luxchat.blob.core.windows.net/assets/icon.ico|' src/vector/static/unable-to-load.html && \
  sed -i 's|Luxchat4Gov|Luxchat|' src/vector/static/unable-to-load.html 


RUN python3 /app/merge_translations.py


RUN yarn --network-timeout=200000 --pure-lockfile install && \
    yarn build && \
    export $(cat .env) && \
    cat /dev/null > version && \ 
    echo $VERSION >> version && \
    mv version ./webapp

# Copy the config now so that we don't create another layer in the app image
RUN mkdir -p /app/webapp/ && cp /app/config.json /app/webapp/config.json

# App
FROM nginx:alpine-slim

COPY --from=builder /app/webapp /app

# Override default nginx config. Templates in `/etc/nginx/templates` are passed
# through `envsubst` by the nginx docker image entry point.
COPY ./element-web/docker/nginx-templates/* /etc/nginx/templates/

# nginx user must own the cache and etc directory to write cache and tweak the nginx config
RUN chown -R nginx:0 /var/cache/nginx /etc/nginx
RUN chmod -R g+w /var/cache/nginx /etc/nginx

RUN rm -rf /usr/share/nginx/html \
  && ln -s /app /usr/share/nginx/html

# HTTP listen port
ENV ELEMENT_WEB_PORT=80