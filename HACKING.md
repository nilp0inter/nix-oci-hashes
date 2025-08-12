# Hacking Guide

This guide is for developers who want to fork and contribute to nix-oci-hashes or run their own instance.

## Setting Up Your Fork

If you're forking this repository to run your own instance, you'll need to set up a Personal Access Token (PAT) for the automated workflow to create pull requests.

### 1. Create a Fine-Grained Personal Access Token

1. Go to GitHub Settings: https://github.com/settings/tokens?type=beta
2. Click **"Generate new token"** → **"Fine-grained personal access token"**
3. Configure the token:
   - **Token name**: Something descriptive like `nix-oci-hashes-pr-bot`
   - **Expiration**: Choose 90 days or set a custom expiration
   - **Repository access**: Select "Selected repositories" and add your forked repository

4. Set the required **Repository permissions**:
   - **Contents**: Read and Write (needed to create branches and commits)
   - **Pull requests**: Read and Write (needed to create PRs)
   - **Metadata**: Read (automatically selected)

5. Click **"Generate token"** and copy the token immediately (you won't be able to see it again)

### 2. Add the Token to Your Repository

1. Go to your forked repository's settings: `https://github.com/YOUR_USERNAME/nix-oci-hashes/settings/secrets/actions`
2. Click **"New repository secret"**
3. Create the secret:
   - **Name**: `PR_TOKEN`
   - **Secret**: Paste the token you copied
4. Click **"Add secret"**

### 3. Verify the Setup

The workflow will automatically use the `PR_TOKEN` when creating pull requests. You can trigger a test run by:

1. Making a change to `images.json`
2. Pushing to the `main` branch
3. Or manually triggering the workflow from the Actions tab

## Workflow Architecture

The repository uses a unified workflow (`.github/workflows/manage-images.yml`) that:

1. **Builds** the manage-images script
2. **Generates** version Dockerfiles from `images.json`
3. **Creates** pin Dockerfiles from version files
4. **Harvests** digests into `digests.json`
5. **Creates** a PR with all changes

The PR is then automatically merged by Mergify based on the labels `update` and `digests`.

## Local Development

### Running the Scripts Locally

You can test the image management scripts locally:

```bash
# Build the script
nix build .#manage-images

# Run individual commands
nix run .#manage-images -- generate-versions
nix run .#manage-images -- generate-pins
nix run .#manage-images -- harvest-digests

# Or run with Python directly
python3 nix/scripts/manage-images.py generate-versions
python3 nix/scripts/manage-images.py generate-pins
python3 nix/scripts/manage-images.py harvest-digests
```

### Testing Changes

Before pushing changes:

1. Ensure the script builds: `nix build .#manage-images`
2. Test each subcommand works as expected
3. Verify the Python script has proper formatting (single newline at EOF)

## Adding New Images

To add new software to track:

1. Edit `images.json` and add an entry:
```json
{
  "image": "docker.io/example/app",
  "platforms": ["linux/amd64", "linux/arm64"],
  "initialMajor": ["1"],
  "initialMajorMinor": ["1.2"],
  "initialMajorMinorPatch": ["1.2.3"]
}
```

2. Push to main - the workflow will:
   - Generate version Dockerfiles
   - Create pin Dockerfiles
   - Wait for Renovate to add digests
   - Update `digests.json`

## Troubleshooting

### PR Creation Fails

If the workflow fails at the "Create Pull Request" step:

1. Check that `PR_TOKEN` is properly set in repository secrets
2. Verify the token hasn't expired
3. Ensure the token has the correct permissions (Contents: R/W, Pull requests: R/W)

### Script Build Fails

If the "Build manage-images script" step fails:

1. Check that `nix/scripts/manage-images.py` ends with exactly one newline
2. Verify Python syntax is correct
3. Run `nix build .#manage-images` locally to see detailed errors

### Mergify Not Auto-Merging

If PRs aren't being auto-merged:

1. Check that PRs have both `update` and `digests` labels
2. Verify `.mergify.yml` configuration is correct
3. Ensure all CI checks are passing

## Contributing

When contributing to this repository:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally with `nix build .#manage-images`
5. Submit a pull request

For significant changes, please open an issue first to discuss what you would like to change.