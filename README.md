# Homelab

Docker Compose stacks deployed through Portainer. Runtime variables and secrets
are configured in Portainer, not committed to this repository.

## Update validation

The **Validate updates** GitHub Actions check runs on every pull request, on
changes to `main`, and for merge queues. It validates:

- `renovate.json` with the pinned Renovate configuration validator;
- every tracked Compose stack using `docker compose config`;
- availability of each exact image reference and its `linux/amd64` manifest.

The check reads registry metadata only. It does not pull image layers, start
containers, connect to Proxmox, or deploy anything. Required Portainer variables
remain unexpanded, and local `.env` / service environment files are not loaded.

Run the checks locally with Python 3, Docker CLI / Compose, Node.js 24, and
[regctl](https://regclient.org/cli/regctl/image/inspect/). CI pins regctl to 0.11.7
and verifies its download checksum:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/validate_stacks.py --compose-only
npx --yes --package renovate@44.178.3 -- renovate-config-validator --strict --no-global renovate.json
python3 scripts/validate_stacks.py
```

Registry checks require network access. Images must be anonymously readable or
regctl must already be authenticated to the registry. Registry errors
fail the check; they are not silently skipped.

Require **Validate updates** in the protection rules for `main` before relying
on this check to gate merges. Portainer polling deploys changes after they reach
`main`; a check on a push cannot prevent that deployment.

These checks do not prove application compatibility, validate secret values,
test database migrations, or scan images for vulnerabilities. Major upgrades
still need review and stateful services still need restorable backups. Automerge
is not enabled by this workflow.
