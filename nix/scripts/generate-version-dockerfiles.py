#!/usr/bin/env python3

import json
import sys
from pathlib import Path


def sanitize_image_name(image):
    """Convert image name to filesystem-safe format"""
    # Replace registry slashes and special chars
    return image.replace('/', '_').replace(':', '_').replace('.', '_')


def sanitize_tag(tag):
    """Convert tag to filesystem-safe format"""
    return tag.replace('.', '_').replace('/', '_')


def create_dockerfile_with_tag(image, platform, tag):
    """Create a Dockerfile with FROM directive and specific tag"""
    dockerfile_content = f"FROM --platform={platform} {image}:{tag}\n"
    return dockerfile_content


def main():
    # Read images.json
    images_file = Path("images.json")
    if not images_file.exists():
        print("Error: images.json not found", file=sys.stderr)
        sys.exit(1)

    with open(images_file) as f:
        images = json.load(f)

    created_version_files = []
    created_pin_files = []

    for item in images:
        image = item["image"]
        platforms = item["platforms"]
        safe_image_name = sanitize_image_name(image)

        # Process version Dockerfiles
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

                        created_version_files.append(str(dockerfile_path))
                        print(f"Created version: {dockerfile_path}")

        # Process pin Dockerfiles for all tags
        all_tags = []
        all_tags.extend(item.get("initialMajor", []))
        all_tags.extend(item.get("initialMajorMinor", []))
        all_tags.extend(item.get("initialMajorMinorPatch", []))

        for tag in all_tags:
            safe_tag = sanitize_tag(tag)
            for platform in platforms:
                safe_platform = platform.replace('/', '_')
                pin_path = Path(f"nix/_dockerfiles/pins/{safe_image_name}/{safe_platform}/{safe_tag}/Dockerfile")

                if not pin_path.exists():
                    # Create directory structure
                    pin_path.parent.mkdir(parents=True, exist_ok=True)

                    # Create Dockerfile with tag
                    dockerfile_content = create_dockerfile_with_tag(image, platform, tag)
                    pin_path.write_text(dockerfile_content)

                    created_pin_files.append(str(pin_path))
                    print(f"Created pin: {pin_path}")

    # Report results
    total_created = len(created_version_files) + len(created_pin_files)

    if total_created > 0:
        if created_version_files:
            print(f"\nCreated {len(created_version_files)} new version Dockerfile(s)")
        if created_pin_files:
            print(f"Created {len(created_pin_files)} new pin Dockerfile(s)")
        sys.exit(0)  # Exit with success to trigger commit in CI
    else:
        print("No new Dockerfiles needed")
        sys.exit(0)


if __name__ == "__main__":
    main()
