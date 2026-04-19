#!/bin/sh
set -euo pipefail

wget -O docker-compose.yml https://raw.githubusercontent.com/flexusjan/homelab/main/docker-compose/portainer/docker-compose.yml
docker compose pull
docker compose up -d