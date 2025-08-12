# nix-oci-hashes

Automated, versioned, and reproducible OCI/Docker image references for NixOS systems.

## The Problem

When using `virtualisation.oci-containers` in NixOS, users face a dilemma:

1. **Without pinning**: Using `image = "nginx:1.24"` means the actual image can change between deployments, breaking reproducibility
2. **With manual pinning**: Using `image = "nginx:1.24@sha256:abc..."` ensures reproducibility but requires manual updates
3. **Update workflow mismatch**: `nix flake update` updates all Nix dependencies but doesn't touch Docker image hashes

This creates a gap where NixOS users must choose between reproducibility and maintainability for their containerized services.

## The Solution

This flake provides automatically updated, hash-pinned Docker image references that integrate seamlessly with the Nix ecosystem:

- **Automated updates**: Renovate bot continuously updates image hashes via pull requests
- **Version preservation**: Major and minor versions are respected based on directory structure
- **Platform support**: Multi-architecture support (linux/amd64, linux/arm64)
- **Flake integration**: Updates via standard `nix flake update` workflow
- **Full reproducibility**: Every image reference includes its SHA256 digest
- **Git-tracked history**: All updates are versioned through Git commits

## Usage

### Basic Example

Add this flake to your NixOS configuration:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    nix-oci-hashes.url = "github:nilp0inter/nix-oci-hashes";
  };

  outputs = { self, nixpkgs, nix-oci-hashes, ... }: {
    nixosConfigurations.myserver = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ({ ... }: {
          virtualisation.oci-containers.containers = {
            home-assistant = {
              image = nix-oci-hashes.ociHashes."docker.io/homeassistant/home-assistant"."2024.12"."linux/amd64";
              ports = ["8123:8123"];
            };
            
            nextcloud = {
              image = nix-oci-hashes.ociHashes."docker.io/nextcloud"."29"."linux/amd64";
              environment = {
                POSTGRES_HOST = "postgres";
              };
            };
          };
        })
      ];
    };
  };
}
```

The `image` values will resolve to fully pinned references like:
- `docker.io/homeassistant/home-assistant:2024.12@sha256:abc123...`
- `docker.io/nextcloud:29@sha256:def456...`

### Platform-Specific Images

The flake supports multiple platforms for each image:

```nix
# For AMD64 systems
image = nix-oci-hashes.ociHashes."docker.io/nextcloud"."29"."linux/amd64";

# For ARM64 systems (e.g., Raspberry Pi 4, Apple Silicon)
image = nix-oci-hashes.ociHashes."docker.io/nextcloud"."29"."linux/arm64";
```

### Updating Images

Simply run:
```bash
nix flake update nix-oci-hashes
```

This updates your lock file to the latest commit, which includes all the latest image hashes updated by Renovate.

### Available Images

Check available images and versions:
```bash
# List all available images
nix eval github:nilp0inter/nix-oci-hashes#ociHashes --apply builtins.attrNames --json | jq

# List versions for a specific image
nix eval 'github:nilp0inter/nix-oci-hashes#ociHashes."docker.io/homeassistant/home-assistant"' --apply builtins.attrNames --json | jq

# List platforms for a specific image version
nix eval 'github:nilp0inter/nix-oci-hashes#ociHashes."docker.io/homeassistant/home-assistant"."2024.12"' --apply builtins.attrNames --json | jq

# Get specific image reference
nix eval 'github:nilp0inter/nix-oci-hashes#ociHashes."docker.io/homeassistant/home-assistant"."2024.12"."linux/amd64"' --raw
```

Currently tracked images include:
- **Home Automation**: Home Assistant
- **Media Servers**: Plex Media Server
- **Security Cameras**: Frigate
- **Cloud Storage**: Nextcloud
- **Document Management**: Paperless-ngx
- **Chat**: Matrix Synapse
- **Authentication**: Authelia, Keycloak
- **Password Management**: Vaultwarden
- **CI/CD**: GitLab CE

## Repository Structure

```
.
├── images.json                    # Defines which images and platforms to track
├── digests.json                   # Generated JSON with all image references
├── nix/
│   ├── flake.nix                 # Main flake definition
│   ├── oci-hashes.nix            # Exposes digests.json as flake output
│   ├── packages.nix              # Defines automation scripts as Nix packages
│   ├── scripts/
│   │   ├── generate-version-dockerfiles.py  # Creates version Dockerfiles
│   │   ├── harvest-tags.py                  # Creates pin Dockerfiles from tagged versions
│   │   └── collect-digests.py              # Generates digests.json from pins
│   └── _dockerfiles/
│       ├── versions/             # Version-constrained Dockerfiles (managed by CI)
│       │   ├── major/           # Only major version updates
│       │   ├── major-minor/     # Major and minor updates
│       │   └── major-minor-patch/ # All updates
│       └── pins/                # Pinned Dockerfiles with specific tags (managed by CI)
└── .github/workflows/
    ├── generate-version-dockerfiles.yml  # Creates version Dockerfiles from images.json
    ├── harvest-tags.yml                  # Creates pin Dockerfiles when Renovate adds tags
    └── collect-digests.yml              # Updates digests.json from pin Dockerfiles
```

## Contributing

### Adding New Software

1. **Edit `images.json`**:
   ```json
   {
     "image": "docker.io/grafana/grafana",
     "platforms": ["linux/amd64", "linux/arm64"]
   }
   ```
   
   Use the fully qualified image name including the registry (docker.io, ghcr.io, etc.).

2. **Submit a pull request**. The automation will:
   - Create Dockerfiles in all version strategy directories
   - Renovate will add appropriate version tags based on the directory
   - Pin Dockerfiles will be created with those tags
   - Renovate will add SHA256 digests to the pin Dockerfiles
   - `digests.json` will be updated with all references

### Version Strategies

The system supports three version constraint strategies:

- **`major/`**: Only updates to new major versions (e.g., 1.x → 2.x)
- **`major-minor/`**: Updates major and minor versions (e.g., 1.2.x → 1.3.x)
- **`major-minor-patch/`**: Updates all versions including patches (e.g., 1.2.3 → 1.2.4)

Renovate respects these constraints when updating tags in the version Dockerfiles.

## How It Works

1. **`images.json`**: Defines which images and platforms to track
2. **CI Workflow**: Creates version Dockerfiles with `:latest` tag for all version strategies
3. **Renovate Bot**: Adds specific version tags to version Dockerfiles based on directory constraints
4. **CI Workflow**: Harvests tags from version Dockerfiles and creates pin Dockerfiles
5. **Renovate Bot**: Adds SHA256 digests to pin Dockerfiles
6. **CI Workflow**: Collects all references from pin Dockerfiles into `digests.json`
7. **Nix Flake**: Exposes `digests.json` as structured attribute set
8. **Mergify**: Automatically merges Renovate PRs after checks pass

### Automatic Cleanup

When images or platforms are removed from `images.json`, the automation scripts automatically:
- Remove orphaned version Dockerfiles
- Remove orphaned pin Dockerfiles
- Update `digests.json` to reflect the changes
- Clean up empty directories

## Benefits

- **Zero Maintenance**: Once configured, images stay updated automatically
- **Reproducible**: Every deployment uses the exact same image
- **Multi-Platform**: Native support for different architectures
- **Auditable**: Git history shows exactly when and what was updated
- **Flexible**: Supports multiple versioning strategies and registries
- **Native Integration**: Works seamlessly with `nix flake update`

## License

MIT

## Acknowledgments

This project leverages:
- [Renovate](https://docs.renovatebot.com/) for automated dependency updates
- [Mergify](https://mergify.com/) for automated PR merging
- [NixOS](https://nixos.org/) for reproducible system configuration