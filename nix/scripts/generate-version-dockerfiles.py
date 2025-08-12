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


def get_expected_version_paths(images):
    """Get all expected version Dockerfile paths based on images.json"""
    expected = set()

    for item in images:
        image = item["image"]
        platforms = item["platforms"]
        safe_image_name = sanitize_image_name(image)

        # Check each version strategy
        strategies = {
            "major": item.get("initialMajor", []),
            "major-minor": item.get("initialMajorMinor", []),
            "major-minor-patch": item.get("initialMajorMinorPatch", [])
        }

        for strategy, tags in strategies.items():
            # Only create if there are initial tags
            if tags:
                for platform in platforms:
                    safe_platform = platform.replace('/', '_')
                    dockerfile_path = Path(f"nix/_dockerfiles/versions/{strategy}/{safe_image_name}/{safe_platform}/Dockerfile")
                    expected.add(dockerfile_path)

    return expected


def get_expected_pin_paths(images):
    """Get all expected pin Dockerfile paths based on images.json"""
    expected = set()

    for item in images:
        image = item["image"]
        platforms = item["platforms"]
        safe_image_name = sanitize_image_name(image)

        # Collect all tags from all strategies
        all_tags = []
        all_tags.extend(item.get("initialMajor", []))
        all_tags.extend(item.get("initialMajorMinor", []))
        all_tags.extend(item.get("initialMajorMinorPatch", []))

        # Create pin paths for all tags
        for tag in all_tags:
            safe_tag = sanitize_tag(tag)
            for platform in platforms:
                safe_platform = platform.replace('/', '_')
                pin_path = Path(f"nix/_dockerfiles/pins/{safe_image_name}/{safe_platform}/{safe_tag}/Dockerfile")
                expected.add(pin_path)

    return expected


def get_existing_dockerfiles(base_dir):
    """Get all existing Dockerfiles in a directory"""
    if not base_dir.exists():
        return set()
    return set(base_dir.rglob("Dockerfile"))


def remove_orphaned_dockerfiles(expected_paths, existing_paths, base_dir):
    """Remove Dockerfiles that are no longer expected"""
    removed_files = []
    orphaned = existing_paths - expected_paths

    for dockerfile_path in orphaned:
        # Remove the Dockerfile
        dockerfile_path.unlink()
        removed_files.append(str(dockerfile_path))
        print(f"Removed: {dockerfile_path}")

        # Clean up empty directories
        parent = dockerfile_path.parent
        while parent != base_dir and parent.exists():
            try:
                # Only remove if directory is empty
                parent.rmdir()
                print(f"Removed empty directory: {parent}")
                parent = parent.parent
            except OSError:
                # Directory not empty, stop cleaning
                break

    return removed_files


def main():
    # Read images.json
    images_file = Path("images.json")
    if not images_file.exists():
        print("Error: images.json not found", file=sys.stderr)
        sys.exit(1)

    with open(images_file) as f:
        images = json.load(f)

    # Get expected and existing paths for versions
    versions_dir = Path("nix/_dockerfiles/versions")
    expected_version_paths = get_expected_version_paths(images)
    existing_version_paths = get_existing_dockerfiles(versions_dir)

    # Get expected and existing paths for pins
    pins_dir = Path("nix/_dockerfiles/pins")
    expected_pin_paths = get_expected_pin_paths(images)
    existing_pin_paths = get_existing_dockerfiles(pins_dir)

    # Remove orphaned files first
    removed_version_files = remove_orphaned_dockerfiles(expected_version_paths, existing_version_paths, versions_dir)
    removed_pin_files = remove_orphaned_dockerfiles(expected_pin_paths, existing_pin_paths, pins_dir)

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
    created = len(created_version_files) + len(created_pin_files)
    removed = len(removed_version_files) + len(removed_pin_files)
    total_changes = created + removed
    if total_changes > 0:
        if created_version_files:
            print(f"\nCreated {len(created_version_files)} new version Dockerfile(s)")
        if created_pin_files:
            print(f"Created {len(created_pin_files)} new pin Dockerfile(s)")
        if removed_version_files:
            print(f"Removed {len(removed_version_files)} orphaned version Dockerfile(s)")
        if removed_pin_files:
            print(f"Removed {len(removed_pin_files)} orphaned pin Dockerfile(s)")
        sys.exit(0)  # Exit with success to trigger commit in CI
    else:
        print("No changes needed")
        sys.exit(0)


if __name__ == "__main__":
    main()
