# The project's Python base image, made to trust a Claude Code cloud session's
# TLS proxy. docker-up.sh builds it; compose.cloud.yaml swaps it in for the
# `FROM python:...` in the project's Dockerfile.
ARG PYTHON_IMAGE=python:3.14.4-slim-bookworm
FROM ${PYTHON_IMAGE}
COPY proxy-ca.crt /tmp/proxy-ca.crt
# The proxy only carries HTTPS, so apt switches to its HTTPS mirrors.
RUN cat /tmp/proxy-ca.crt >> /etc/ssl/certs/ca-certificates.crt \
    && rm /tmp/proxy-ca.crt \
    && sed -i 's#http://deb.debian.org#https://deb.debian.org#' /etc/apt/sources.list.d/debian.sources
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
