import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import validate_stacks as checks


IMAGE = "example/app:1.2.3@sha256:" + "d" * 64


class ImageChecks(unittest.TestCase):
    def test_wrong_architecture_or_attestation_is_rejected(self):
        for os_name, architecture in [("linux", "arm64"), ("unknown", "unknown"), ("windows", "amd64")]:
            with self.subTest(os=os_name, architecture=architecture):
                with patch.object(checks, "image_configuration", return_value={"os": os_name, "architecture": architecture}):
                    with self.assertRaisesRegex(checks.ValidationError, "not available for linux/amd64"):
                        checks.validate_image(IMAGE, Path("."))

    def test_unavailable_image_is_not_a_success(self):
        with patch.object(checks, "image_configuration", side_effect=checks.ValidationError("manifest unknown")):
            with self.assertRaisesRegex(checks.ValidationError, "manifest unknown"):
                checks.validate_image(IMAGE, Path("."))

    def test_exact_pinned_image_and_host_platform_are_checked(self):
        with patch.object(checks, "command", return_value=json.dumps({"os": "linux", "architecture": "amd64"})) as run:
            checks.validate_image(IMAGE, Path("."))
        args = run.call_args.args[0]
        self.assertEqual(args[-1], IMAGE)
        self.assertEqual(args[args.index("--platform") + 1], "linux/amd64")

    def test_rate_limit_is_retried_but_not_ignored(self):
        with patch.object(checks, "command", side_effect=checks.ValidationError("429 Too Many Requests")) as run:
            with patch.object(checks.time, "sleep"):
                with self.assertRaisesRegex(checks.ValidationError, "429"):
                    checks.image_configuration(IMAGE, Path("."))
        self.assertEqual(run.call_count, 3)


class ComposeChecks(unittest.TestCase):
    def test_unknown_dependency_is_rejected_even_if_compose_renders_it(self):
        config = {"services": {"app": {"image": IMAGE, "depends_on": {"missing": {"required": True}}}}}
        with patch.object(checks, "command", side_effect=[
            "docker-compose/app/compose.yaml\0", json.dumps(config),
        ]):
            with self.assertRaisesRegex(checks.ValidationError, "unknown dependency"):
                checks.compose_images(Path("."))

    def test_no_compose_files_is_an_error(self):
        with patch.object(checks, "command", return_value=""):
            with self.assertRaisesRegex(checks.ValidationError, "No tracked"):
                checks.compose_images(Path("."))

    def test_failed_compose_validation_blocks_images(self):
        with patch.object(checks, "command", side_effect=[
            "docker-compose/app/compose.yaml\0", checks.ValidationError("invalid port"),
        ]):
            with self.assertRaisesRegex(checks.ValidationError, "compose.yaml: invalid port"):
                checks.compose_images(Path("."))

    def test_required_portainer_variables_are_left_unexpanded(self):
        config = {"services": {"app": {"image": IMAGE, "environment": {"PASSWORD": "${PASSWORD:?required}"}}}}
        with patch.object(checks, "command", side_effect=[
            "docker-compose/app/compose.yaml\0", json.dumps(config),
        ]) as run:
            self.assertIn(IMAGE, checks.compose_images(Path(".")))
        args = run.call_args.args[0]
        self.assertIn("--no-interpolate", args)
        self.assertIn("--no-env-resolution", args)
        self.assertEqual(args[args.index("--env-file") + 1], "/dev/null")


if __name__ == "__main__":
    unittest.main()
