#!/usr/bin/env python3

import json
import re
from pathlib import Path


def parse_dockerfile(filepath):
    """Parse a Dockerfile and extract the FROM line details"""
    with open(filepath) as f:
        content = f.read()

    # Match FROM line with optional platform and image:tag@digest
    from_pattern = r'^FROM\s+(?:--platform=([^\s]+)\s+)?([^\s]+?)(?::([^\s@]+))?(?:@sha256:([a-f0-9]{64}))?\s*(?:AS\s+.*)?$'

    for line in content.splitlines():
        match = re.match(from_pattern, line, re.IGNORECASE)
        if match:
            platform = match.group(1)
            image = match.group(2)
            tag = match.group(3)
            digest = match.group(4)

            # Default tag to 'latest' if not specified
            if not tag:
                tag = 'latest'

            # Default platform if not specified
            if not platform:
                platform = 'linux/amd64'  # Common default

            return {
                'platform': platform,
                'image': image,
                'tag': tag,
                'digest': digest
            }
    return None


def collect_digests():
    """Collect all Docker image digests from pins directory"""
    pins_dir = Path("nix/_dockerfiles/pins")

    if not pins_dir.exists():
        return {}

    digests = {}

    # Find all Dockerfiles in the pins directory
    for dockerfile_path in pins_dir.rglob("Dockerfile"):
        parsed = parse_dockerfile(dockerfile_path)

        if parsed:
            image = parsed['image']
            tag = parsed['tag']
            platform = parsed['platform']

            # Initialize nested structure
            if image not in digests:
                digests[image] = {}
            if tag not in digests[image]:
                digests[image][tag] = {}

            # Build the full reference
            if parsed['digest']:
                reference = f"{image}:{tag}@sha256:{parsed['digest']}"
            else:
                reference = f"{image}:{tag}"

            # Store by platform
            digests[image][tag][platform] = reference

    return digests


def main():
    """Main function to collect digests and write to JSON file"""
    digests = collect_digests()

    # Count total entries
    total_entries = sum(
        len(platforms)
        for image_tags in digests.values()
        for platforms in image_tags.values()
    )

    # Write to digests.json
    output_file = Path("digests.json")
    with open(output_file, 'w') as f:
        json.dump(digests, f, indent=2, sort_keys=True)

    print(f"Collected {total_entries} image references from {len(digests)} images")
    print(f"Written to {output_file}")


if __name__ == "__main__":
    main()
