#!/usr/bin/env python3

import json
import sys
import shutil
from pathlib import Path


def sanitize_image_name(image):
    """Convert image name to filesystem-safe format"""
    # Replace registry slashes and special chars
    return image.replace('/', '_').replace(':', '_').replace('.', '_')


def create_dockerfile(image, platform, version_dir):
    """Create a Dockerfile with FROM directive"""
    dockerfile_content = f"FROM --platform={platform} {image}\n"
    return dockerfile_content


def get_expected_paths(images):
    """Get all expected Dockerfile paths based on images.json"""
    expected = set()
    version_strategies = ["major", "major-minor", "major-minor-patch"]

    for item in images:
        image = item["image"]
        platforms = item["platforms"]
        safe_image_name = sanitize_image_name(image)

        for strategy in version_strategies:
            for platform in platforms:
                safe_platform = platform.replace('/', '_')
                dockerfile_path = Path(f"nix/_dockerfiles/versions/{strategy}/{safe_image_name}/{safe_platform}/Dockerfile")
                expected.add(dockerfile_path)

    return expected


def get_existing_version_dockerfiles():
    """Get all existing Dockerfiles in versions directory"""
    versions_dir = Path("nix/_dockerfiles/versions")
    if not versions_dir.exists():
        return set()

    return set(versions_dir.rglob("Dockerfile"))


def remove_orphaned_dockerfiles(expected_paths, existing_paths):
    """Remove Dockerfiles that are no longer in images.json"""
    removed_files = []
    orphaned = existing_paths - expected_paths

    for dockerfile_path in orphaned:
        # Remove the Dockerfile
        dockerfile_path.unlink()
        removed_files.append(str(dockerfile_path))
        print(f"Removed: {dockerfile_path}")

        # Clean up empty directories
        parent = dockerfile_path.parent
        while parent != Path("nix/_dockerfiles/versions") and parent.exists():
            try:
                # Only remove if directory is empty
                parent.rmdir()
                print(f"Removed empty directory: {parent}")
                parent = parent.parent
            except OSError:
                # Directory not empty, stop cleaning
                break

    return removed_files


def remove_orphaned_pins(images):
    """Remove pin Dockerfiles for images no longer in images.json"""
    pins_dir = Path("nix/_dockerfiles/pins")
    if not pins_dir.exists():
        return []

    # Get all valid image names from images.json
    valid_images = set()
    for item in images:
        safe_image_name = sanitize_image_name(item["image"])
        valid_images.add(safe_image_name)

    removed_pins = []

    # Check each image directory in pins
    for image_dir in pins_dir.iterdir():
        if image_dir.is_dir() and image_dir.name not in valid_images:
            # This image is no longer in images.json, remove entire directory
            shutil.rmtree(image_dir)
            removed_pins.append(str(image_dir))
            print(f"Removed pin directory: {image_dir}")

    return removed_pins


def main():
    # Read images.json
    images_file = Path("images.json")
    if not images_file.exists():
        print("Error: images.json not found", file=sys.stderr)
        sys.exit(1)

    with open(images_file) as f:
        images = json.load(f)

    # Get expected and existing paths
    expected_paths = get_expected_paths(images)
    existing_paths = get_existing_version_dockerfiles()

    # Remove orphaned files first
    removed_files = remove_orphaned_dockerfiles(expected_paths, existing_paths)
    removed_pins = remove_orphaned_pins(images)

    # Version strategies to check
    version_strategies = ["major", "major-minor", "major-minor-patch"]

    created_files = []

    for item in images:
        image = item["image"]
        platforms = item["platforms"]

        # Sanitize image name for directory
        safe_image_name = sanitize_image_name(image)

        for strategy in version_strategies:
            for platform in platforms:
                # Sanitize platform for directory name
                safe_platform = platform.replace('/', '_')

                # Check if Dockerfile exists
                dockerfile_path = Path(f"nix/_dockerfiles/versions/{strategy}/{safe_image_name}/{safe_platform}/Dockerfile")

                if not dockerfile_path.exists():
                    # Create directory structure
                    dockerfile_path.parent.mkdir(parents=True, exist_ok=True)

                    # Create Dockerfile
                    dockerfile_content = create_dockerfile(image, platform, strategy)
                    dockerfile_path.write_text(dockerfile_content)

                    created_files.append(str(dockerfile_path))
                    print(f"Created: {dockerfile_path}")

    if created_files or removed_files or removed_pins:
        if created_files:
            print(f"\nCreated {len(created_files)} new Dockerfile(s)")
        if removed_files:
            print(f"Removed {len(removed_files)} orphaned version Dockerfile(s)")
        if removed_pins:
            print(f"Removed {len(removed_pins)} orphaned pin directories")
        sys.exit(0)  # Exit with success to trigger commit in CI
    else:
        print("No changes needed")
        sys.exit(0)


if __name__ == "__main__":
    main()
