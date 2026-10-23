#!/usr/bin/env python3
"""Validate tracked Compose stacks and image metadata without running containers."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_NAMES = {"compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml"}
# The Proxmox host is x86-64. Image attestations (unknown/unknown) do not count.
PLATFORM = "linux/amd64"


class ValidationError(Exception):
    pass


def command(args, root, timeout=60):
    try:
        result = subprocess.run(
            args, cwd=root, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValidationError(str(exc)) from exc
    if result.returncode:
        raise ValidationError(result.stderr.strip() or f"Command exited with {result.returncode}")
    return result.stdout


def compose_images(root):
    tracked = command(["git", "ls-files", "-z", "--", "docker-compose/"], root)
    files = sorted(Path(p) for p in tracked.split("\0") if p and Path(p).name in COMPOSE_NAMES)
    if not files:
        raise ValidationError("No tracked Compose files found under docker-compose/.")

    images = {}
    errors = []
    for path in files:
        try:
            # Portainer provides runtime variables. Never load local .env files,
            # resolve service env_file entries, or print the rendered configuration.
            output = command(
                [
                    "docker", "compose", "--env-file", "/dev/null", "-f", str(path),
                    "config", "--no-interpolate", "--no-env-resolution",
                    "--no-path-resolution", "--format", "json",
                ], root,
            )
            config = json.loads(output)
            services = config.get("services", {})
            if not services:
                raise ValidationError("No services found.")
            for name, service in services.items():
                image = service.get("image")
                if not isinstance(image, str) or not image or "$" in image:
                    raise ValidationError(f"{name}: a literal image reference is required.")
                if service.get("build"):
                    raise ValidationError(f"{name}: build contexts require a separate build check.")
                if service.get("platform", PLATFORM) != PLATFORM:
                    raise ValidationError(f"{name}: platform must match the host ({PLATFORM}).")
                # With interpolation disabled, Compose versions differ in how
                # thoroughly they check references. Check these explicitly.
                for dependency, options in service.get("depends_on", {}).items():
                    if dependency not in services and options.get("required", True):
                        raise ValidationError(f"{name}: unknown dependency {dependency!r}.")
                for network in service.get("networks", {}):
                    if network not in config.get("networks", {}):
                        raise ValidationError(f"{name}: unknown network {network!r}.")
                for mount in service.get("volumes", []):
                    source = mount.get("source")
                    if mount.get("type") == "volume" and source and source not in config.get("volumes", {}):
                        raise ValidationError(f"{name}: unknown volume {source!r}.")
                images.setdefault(image, []).append(f"{path}: {name}")
            print(f"OK Compose: {path}", flush=True)
        except (ValidationError, ValueError, TypeError) as exc:
            errors.append(f"{path}: {exc}")
    if errors:
        raise ValidationError("\n".join(errors))
    return images


def image_configuration(image, root):
    # regctl resolves the selected platform and retrieves its manifest and
    # image configuration, without downloading filesystem layers.
    args = ["regctl", "image", "inspect", "--platform", PLATFORM, "--format", "raw-body", image]
    for attempt in range(3):
        try:
            return json.loads(command(args, root, timeout=45))
        except ValidationError as exc:
            # Retry transient registry failures, but never turn an unavailable
            # image, denied access, or a timeout into a successful check.
            transient = any(s in str(exc).lower() for s in (
                "429", "toomanyrequests", "too many requests", "timeout", "timed out",
                "connection reset", "temporary failure", "502", "503", "504",
            ))
            if not transient or attempt == 2:
                raise
            time.sleep(2 ** attempt)
        except ValueError as exc:
            raise ValidationError("Registry returned invalid image configuration JSON.") from exc


def validate_image(image, root):
    data = image_configuration(image, root)
    if not isinstance(data, dict):
        raise ValidationError("Unexpected image configuration format.")
    if data.get("os") != "linux" or data.get("architecture") != "amd64":
        raise ValidationError(f"Image is not available for {PLATFORM}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose-only", action="store_true", help="Skip network registry checks.")
    args = parser.parse_args()
    try:
        images = compose_images(ROOT)
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.compose_only:
        return 0

    failed = False
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(validate_image, image, ROOT): image for image in images}
        for future in as_completed(futures):
            image = futures[future]
            try:
                future.result()
                print(f"OK Image ({PLATFORM}): {image}", flush=True)
            except Exception as exc:
                failed = True
                print(f"ERROR Image: {image}\n  Used by: {', '.join(images[image])}\n  {exc}", file=sys.stderr)
    if not failed:
        print(f"Validated {len(images)} unique images without pulling layers or starting containers.")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
