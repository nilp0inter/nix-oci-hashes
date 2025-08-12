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
              image = nix-oci-hashes.ociHashes."docker.io/homeassistant/home-assistant"."2025.8"."linux/amd64";
              ports = ["8123:8123"];
            };
            
            nextcloud = {
              image = nix-oci-hashes.ociHashes."docker.io/nextcloud"."30"."linux/amd64";
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
- `docker.io/homeassistant/home-assistant:2025.8@sha256:abc123...`
- `docker.io/nextcloud:30@sha256:def456...`

### Platform-Specific Images

The flake supports multiple platforms for each image:

```nix
# For AMD64 systems
image = nix-oci-hashes.ociHashes."docker.io/nextcloud"."30"."linux/amd64";

# For ARM64 systems (e.g., Raspberry Pi 4, Apple Silicon)
image = nix-oci-hashes.ociHashes."docker.io/nextcloud"."30"."linux/arm64";
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
nix eval 'github:nilp0inter/nix-oci-hashes#ociHashes."docker.io/homeassistant/home-assistant"."2025.8"' --apply builtins.attrNames --json | jq

# Get specific image reference
nix eval 'github:nilp0inter/nix-oci-hashes#ociHashes."docker.io/homeassistant/home-assistant"."2025.8"."linux/amd64"' --raw
```

## Currently Tracked Images

This flake focuses on applications that benefit from Docker deployment due to their:
- Rapid release cycles
- Complex dependency chains
- Strong Docker-first communities
- Better isolation requirements

| Application | Description | Why Docker? |
|------------|-------------|-------------|
| **Home Assistant** | Home automation platform | Rapid releases (monthly), complex Python dependencies, extensive integrations |
| **Plex Media Server** | Media streaming server | Proprietary software, frequent updates, transcoding dependencies |
| **Open WebUI** | Web interface for LLMs | Fast-moving AI space, complex ML dependencies |
| **Nextcloud** | Self-hosted cloud platform | Complex PHP stack, many plugins, easier upgrades |
| **Vaultwarden** | Bitwarden-compatible server | Rust implementation, simpler than NixOS module |
| **Jellyfin** | Open-source media server | Active development, media codecs, web dependencies |
| **Immich** | Self-hosted photo solution | Very active development, complex ML/AI stack |
| **Paperless-ngx** | Document management | OCR dependencies, machine learning components |

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
     "platforms": ["linux/amd64", "linux/arm64"],
     "initialMajor": ["11"],
     "initialMajorMinor": ["11.4"],
     "initialMajorMinorPatch": ["11.4.2"]
   }
   ```
   
   - Use the fully qualified image name including the registry (docker.io, ghcr.io, etc.)
   - Specify supported platforms
   - Provide initial version tags to bootstrap Renovate's update detection:
     - `initialMajor`: List of major version tags (e.g., `["11"]`)
     - `initialMajorMinor`: List of major.minor tags (e.g., `["11.4"]`)
     - `initialMajorMinorPatch`: List of full version tags (e.g., `["11.4.2"]`)
   - Leave arrays empty if that version strategy doesn't apply

2. **Submit a pull request**. The automation will:
   - Create version Dockerfiles with initial tags
   - Create pin Dockerfiles for all specified tags
   - Renovate will update version tags based on directory constraints
   - Renovate will add SHA256 digests to pin Dockerfiles
   - `digests.json` will be updated with all references

### Version Strategies

The system supports three version constraint strategies:

- **`major/`**: Only updates to new major versions (e.g., 1.x → 2.x)
- **`major-minor/`**: Updates major and minor versions (e.g., 1.2.x → 1.3.x)
- **`major-minor-patch/`**: Updates all versions including patches (e.g., 1.2.3 → 1.2.4)

Renovate respects these constraints when updating tags in the version Dockerfiles.

## How It Works

1. **`images.json`**: Defines which images, platforms, and initial versions to track
2. **CI Workflow**: Creates version Dockerfiles with initial tags for each version strategy
3. **CI Workflow**: Creates pin Dockerfiles for all initial tags
4. **Renovate Bot**: Updates version tags in version Dockerfiles based on directory constraints
5. **CI Workflow**: Harvests new tags from version Dockerfiles and creates new pin Dockerfiles
6. **Renovate Bot**: Adds SHA256 digests to pin Dockerfiles
7. **CI Workflow**: Collects all references from pin Dockerfiles into `digests.json`
8. **Nix Flake**: Exposes `digests.json` as structured attribute set
9. **Mergify**: Automatically merges Renovate PRs after checks pass

## Benefits

- **Zero Maintenance**: Once configured, images stay updated automatically
- **Reproducible**: Every deployment uses the exact same image
- **Multi-Platform**: Native support for different architectures
- **Auditable**: Git history shows exactly when and what was updated
- **Flexible**: Supports multiple versioning strategies and registries
- **Native Integration**: Works seamlessly with `nix flake update`
- **Docker-First Apps**: Focuses on applications that truly benefit from containerization

## License

MIT

## Acknowledgments

This project leverages:
- [Renovate](https://docs.renovatebot.com/) for automated dependency updates
- [Mergify](https://mergify.com/) for automated PR merging
- [NixOS](https://nixos.org/) for reproducible system configuration
