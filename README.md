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
            nginx = {
              image = nix-oci-hashes.ociHashes.nginx."1.24";
              ports = ["80:80"];
            };
            
            postgres = {
              image = nix-oci-hashes.ociHashes.postgres."16";
              environment = {
                POSTGRES_PASSWORD = "secret";
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
- `nginx:1.24@sha256:f6daac2445b0ce70e64d77442ccf62839f3f1b4c24bf6746a857eff014e798c8`
- `postgres:16@sha256:fec2740c517838d4f582e48a8a9a1cb51082af3dcae59e9b12a66ec262302b97`

### Updating Images

Simply run:
```bash
nix flake update nix-oci-hashes
```

This updates your lock file to the latest commit, which includes all the latest image hashes updated by Renovate.

### Available Images

Check available images and versions:
```bash
# List all available software
nix eval github:nilp0inter/nix-oci-hashes#ociHashes --apply builtins.attrNames --json | jq

# List versions for specific software
nix eval github:nilp0inter/nix-oci-hashes#ociHashes.nginx --apply builtins.attrNames --json | jq

# Get specific image reference
nix eval github:nilp0inter/nix-oci-hashes#ociHashes.nginx.\"1.24\" --raw
```

Currently available images include:
- **Databases**: PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch
- **Web servers**: Nginx, Apache (httpd), Traefik
- **Runtimes**: Node.js, Python
- **Message queues**: RabbitMQ
- **CI/CD**: Jenkins
- **Applications**: Open WebUI

## Repository Structure

TODO

## Contributing

### Adding New Software

1. **Determine version strategy**:
   TODO

2. **Create the directory structure**:
   TODO

3. **Add the Dockerfile**:
   ```dockerfile
   FROM image:tag
   ```
   
   Example for PostgreSQL 17:
   TODO

4. **Submit a pull request**. Renovate will automatically:
   - Add the SHA256 digest to the image reference
   - Keep it updated with new releases
   - Respect the version constraints based on directory placement


## How It Works

1. **Dockerfiles**: Each Dockerfile contains a single `FROM` line with the image reference
2. **Renovate Bot**: Monitors all Dockerfiles and creates PRs to update image digests
3. **Version Constraints**: 
   TODO
4. **Mergify**: Automatically merges Renovate PRs after checks pass
5. **Nix Flake**: Parses all Dockerfiles at evaluation time and exposes image references
6. **Git History**: Every update is a commit, providing a complete audit trail

## Benefits

- **Zero Maintenance**: Once configured, images stay updated automatically
- **Reproducible**: Every deployment uses the exact same image
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
