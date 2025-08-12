#!/usr/bin/env python3

import argparse
import json
import re
import sys
from pathlib import Path


def sanitize_image_name(image):
    """Convert image name to filesystem-safe format"""
    return image.replace('/', '_').replace(':', '_').replace('.', '_')


def sanitize_tag(tag):
    """Convert tag to filesystem-safe format"""
    return tag.replace('.', '_').replace('/', '_')


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
                platform = 'linux/amd64'

            return {
                'platform': platform,
                'image': image,
                'tag': tag,
                'digest': digest,
                'full_line': line
            }
    return None


def create_dockerfile_with_tag(image, platform, tag):
    """Create a Dockerfile with FROM directive and specific tag"""
    return f"FROM --platform={platform} {image}:{tag}\n"


def generate_versions():
    """Generate version Dockerfiles from images.json (Step 1)"""
    images_file = Path("images.json")
    if not images_file.exists():
        print("Error: images.json not found", file=sys.stderr)
        return 1

    with open(images_file) as f:
        images = json.load(f)

    created_files = []

    for item in images:
        image = item["image"]
        platforms = item["platforms"]
        safe_image_name = sanitize_image_name(image)

        # Process version Dockerfiles only (not pins)
        strategies = {
            "major": item.get("initialMajor", []),
            "major-minor": item.get("initialMajorMinor", []),
            "major-minor-patch": item.get("initialMajorMinorPatch", [])
        }

        for strategy, tags in strategies.items():
            if tags:  # Only create if there are initial tags
                # Use the first tag for the version Dockerfile
                tag = tags[0]
                for platform in platforms:
                    safe_platform = platform.replace('/', '_')
                    dockerfile_path = Path(f"nix/_dockerfiles/versions/{strategy}/{safe_image_name}/{safe_platform}/Dockerfile")

                    if not dockerfile_path.exists():
                        # Create directory structure
                        dockerfile_path.parent.mkdir(parents=True, exist_ok=True)

                        # Create Dockerfile with tag
                        dockerfile_content = create_dockerfile_with_tag(image, platform, tag)
                        dockerfile_path.write_text(dockerfile_content)

                        created_files.append(str(dockerfile_path))
                        print(f"Created version: {dockerfile_path}")

    if created_files:
        print(f"\nCreated {len(created_files)} new version Dockerfile(s)")
    else:
        print("No new version Dockerfiles needed")

    return 0


def generate_pins():
    """Generate pin Dockerfiles from both version Dockerfiles and images.json (Step 2)"""
    pins_dir = Path("nix/_dockerfiles/pins")
    versions_dir = Path("nix/_dockerfiles/versions")
    created_files = []

    # First, harvest tags from version Dockerfiles
    if versions_dir.exists():
        for dockerfile_path in versions_dir.rglob("Dockerfile"):
            parsed = parse_dockerfile(dockerfile_path)

            if not parsed or not parsed['tag']:
                continue

            image = parsed['image']
            tag = parsed['tag']
            platform = parsed['platform']

            # Sanitize for filesystem
            safe_image = sanitize_image_name(image)
            safe_platform = platform.replace('/', '_')
            safe_tag = sanitize_tag(tag)

            # Check if pin Dockerfile already exists
            pin_dockerfile_path = pins_dir / safe_image / safe_platform / safe_tag / "Dockerfile"

            if not pin_dockerfile_path.exists():
                # Create directory structure
                pin_dockerfile_path.parent.mkdir(parents=True, exist_ok=True)

                # Create Dockerfile with the full FROM line including tag
                dockerfile_content = create_dockerfile_with_tag(image, platform, tag)
                pin_dockerfile_path.write_text(dockerfile_content)
                created_files.append(str(pin_dockerfile_path))
                print(f"Created pin from version: {pin_dockerfile_path}")

    # Second, create pins from images.json initial tags
    images_file = Path("images.json")
    if images_file.exists():
        with open(images_file) as f:
            images = json.load(f)

        for item in images:
            image = item["image"]
            platforms = item["platforms"]
            safe_image_name = sanitize_image_name(image)

            # Collect all initial tags
            all_tags = []
            all_tags.extend(item.get("initialMajor", []))
            all_tags.extend(item.get("initialMajorMinor", []))
            all_tags.extend(item.get("initialMajorMinorPatch", []))

            for tag in all_tags:
                safe_tag = sanitize_tag(tag)
                for platform in platforms:
                    safe_platform = platform.replace('/', '_')
                    pin_path = pins_dir / safe_image_name / safe_platform / safe_tag / "Dockerfile"

                    if not pin_path.exists():
                        # Create directory structure
                        pin_path.parent.mkdir(parents=True, exist_ok=True)

                        # Create Dockerfile with tag
                        dockerfile_content = create_dockerfile_with_tag(image, platform, tag)
                        pin_path.write_text(dockerfile_content)

                        created_files.append(str(pin_path))
                        print(f"Created pin from images.json: {pin_path}")

    if created_files:
        print(f"\nCreated {len(created_files)} new pin Dockerfile(s)")
    else:
        print("No new pin Dockerfiles needed")

    return 0


def harvest_digests():
    """Collect all Docker image digests from pins directory and write to digests.json (Step 3)"""
    pins_dir = Path("nix/_dockerfiles/pins")

    if not pins_dir.exists():
        print("Pins directory not found", file=sys.stderr)
        return 1

    digests = {}
    skipped_count = 0

    # Find all Dockerfiles in the pins directory
    for dockerfile_path in pins_dir.rglob("Dockerfile"):
        parsed = parse_dockerfile(dockerfile_path)

        if parsed:
            if parsed['digest']:
                image = parsed['image']
                tag = parsed['tag']
                platform = parsed['platform']

                # Initialize nested structure
                if image not in digests:
                    digests[image] = {}
                if tag not in digests[image]:
                    digests[image][tag] = {}

                # Build the full reference with digest
                reference = f"{image}:{tag}@sha256:{parsed['digest']}"

                # Store by platform
                digests[image][tag][platform] = reference
            else:
                # Count skipped entries (no digest yet)
                skipped_count += 1

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

    print(f"Collected {total_entries} image references with digests from {len(digests)} images")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} Dockerfile(s) without digests (waiting for Renovate)")
    print(f"Written to {output_file}")

    return 0


def main():
    parser = argparse.ArgumentParser(description='Manage OCI image references')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Subcommand for generating version Dockerfiles
    subparsers.add_parser('generate-versions',
                          help='Generate version Dockerfiles from images.json')

    # Subcommand for generating pin Dockerfiles
    subparsers.add_parser('generate-pins',
                          help='Generate pin Dockerfiles from versions and images.json')

    # Subcommand for harvesting digests
    subparsers.add_parser('harvest-digests',
                          help='Harvest digests from pins and update digests.json')

    args = parser.parse_args()

    if args.command == 'generate-versions':
        return generate_versions()
    elif args.command == 'generate-pins':
        return generate_pins()
    elif args.command == 'harvest-digests':
        return harvest_digests()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
