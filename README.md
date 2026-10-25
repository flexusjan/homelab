# Homelab

Docker Compose stacks for my self-hosted services, managed through Portainer.
Each service has its own directory under [`docker-compose/`](docker-compose/).

## Services

| Service | Purpose |
| --- | --- |
| [Portainer](docker-compose/portainer/docker-compose.yml) | Container and stack management |
| [Nginx Proxy Manager](docker-compose/npm/docker-compose.yml) | Reverse proxy and TLS certificates |
| [Homepage](docker-compose/homepage/docker-compose.yml) | Homelab dashboard |
| [Pi-hole](docker-compose/pihole/docker-compose.yml) | Network-wide DNS filtering |
| [Home Assistant](docker-compose/home-assistant/docker-compose.yml) | Smart home automation |
| [Nextcloud](docker-compose/nextcloud/docker-compose.yml) | Private cloud and file sync |
| [Joplin Server](docker-compose/joplin/docker-compose.yml) | Note sync across devices |
| [Paperless-ngx](docker-compose/paperless/docker-compose.yml) | Document archive with OCR |
| [Jace](docker-compose/jace/docker-compose.yml) | Magic: The Gathering collection and price tracking |
| [llama.cpp](docker-compose/llama-cpp/docker-compose.yml) | Local language model inference |
| [SearXNG](docker-compose/searxng/docker-compose.yml) | Web search with MCP access for AI clients |
| [Minecraft](docker-compose/minecraft/docker-compose.yml) | Minecraft Java server |

## Updates

Images are pinned to release or build tags and SHA-256 digests.
[Renovate](renovate.json) automatically merges patch and digest updates after
checks pass. Minor and major updates are reviewed manually.
