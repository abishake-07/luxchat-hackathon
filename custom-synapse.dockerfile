FROM python:3.13 AS builder

WORKDIR /synapse

COPY ./synapse/ /synapse/

#Install rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && . "$HOME/.cargo/env"
ENV PATH="/root/.cargo/bin:$PATH"
RUN rustc --version

RUN python3 -m venv .venv
ENV PATH="/synapse/.venv/bin:$PATH"
RUN pip install -e /synapse/

FROM python:3.13

WORKDIR /synapse

COPY --from=builder /synapse/. /synapse/.

ENV PATH="/synapse/.venv/bin:$PATH"

CMD ["python3", "-m", "synapse.app.homeserver", "--config-path", "/data/homeserver.yaml"]