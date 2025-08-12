#!/usr/bin/env python3

import re
import sys
import shutil
from pathlib import Path


def parse_dockerfile(filepath):
    """Parse a Dockerfile and extract the FROM line details"""
    with open(filepath) as f:
        content = f.read()

    # Match FROM line with optional platform and image:tag
    from_pattern = r'^FROM\s+(?:--platform=([^\s]+)\s+)?([^\s]+?)(?::([^\s@]+))?(?:@sha256:[a-f0-9]{64})?\s*(?:AS\s+.*)?$'

    for line in content.splitlines():
        match = re.match(from_pattern, line, re.IGNORECASE)
        if match:
            platform = match.group(1)
            image = match.group(2)
            tag = match.group(3)
            return {
                'platform': platform,
                'image': image,
                'tag': tag,
                'full_line': line
            }
    return None


def sanitize_for_path(value):
    """Sanitize a value for use in filesystem paths"""
    if not value:
        return None
    return value.replace('/', '_').replace(':', '_').replace('.', '_')


def get_valid_pins_from_versions():
    """Get all valid pin paths based on current version Dockerfiles with tags"""
    versions_dir = Path("nix/_dockerfiles/versions")
    valid_pins = set()

    if not versions_dir.exists():
        return valid_pins

    for dockerfile_path in versions_dir.rglob("Dockerfile"):
        parsed = parse_dockerfile(dockerfile_path)

        if parsed and parsed['tag']:
            safe_image = sanitize_for_path(parsed['image'])
            safe_platform = sanitize_for_path(parsed['platform']) if parsed['platform'] else "default"
            safe_tag = sanitize_for_path(parsed['tag'])

            pin_path = Path("nix/_dockerfiles/pins") / safe_image / safe_platform / safe_tag
            valid_pins.add(pin_path)

    return valid_pins


def main():
    versions_dir = Path("nix/_dockerfiles/versions")
    pins_dir = Path("nix/_dockerfiles/pins")

    if not versions_dir.exists():
        print(f"Versions directory not found: {versions_dir}", file=sys.stderr)
        sys.exit(1)

    # Get valid pins based on current version Dockerfiles
    valid_pins = get_valid_pins_from_versions()

    created_files = []

    # Walk through all version Dockerfiles
    for dockerfile_path in versions_dir.rglob("Dockerfile"):
        # Parse the Dockerfile
        parsed = parse_dockerfile(dockerfile_path)

        if not parsed or not parsed['tag']:
            # Skip if no tag found (Renovate hasn't added it yet)
            continue

        image = parsed['image']
        tag = parsed['tag']
        platform = parsed['platform']

        # Sanitize for filesystem
        safe_image = sanitize_for_path(image)
        safe_platform = sanitize_for_path(platform) if platform else "default"
        safe_tag = sanitize_for_path(tag)

        # Check if pin Dockerfile already exists
        pin_dockerfile_path = pins_dir / safe_image / safe_platform / safe_tag / "Dockerfile"

        if not pin_dockerfile_path.exists():
            # Create directory structure
            pin_dockerfile_path.parent.mkdir(parents=True, exist_ok=True)

            # Create Dockerfile with the full FROM line including tag
            if platform:
                dockerfile_content = f"FROM --platform={platform} {image}:{tag}\n"
            else:
                dockerfile_content = f"FROM {image}:{tag}\n"

            pin_dockerfile_path.write_text(dockerfile_content)
            created_files.append(str(pin_dockerfile_path))
            print(f"Created pin: {pin_dockerfile_path}")

    if created_files:
        if created_files:
            print(f"\nCreated {len(created_files)} new pin Dockerfile(s)")
        sys.exit(0)  # Exit with success to trigger commit in CI
    else:
        print("No changes needed")
        sys.exit(0)


if __name__ == "__main__":
    main()
