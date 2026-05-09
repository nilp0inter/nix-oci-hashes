# Technique: Automated OCI Image Hash Tracking with Renovate

This document explains exactly how `nilp0inter/nix-oci-hashes` keeps Docker/OCI references up to date and digest-pinned, and how to reproduce the same pattern in another repository.

## 1) Goal

Maintain a machine-generated `digests.json` containing image references of the form:

- `<image>:<tag>@sha256:<digest>`

for multiple platforms, while allowing controlled tag updates (major-only, major+minor, or full semver) through Renovate.

---

## 2) Core Files and Their Roles

- `images.json`  
  Source-of-truth input for tracked images/platforms and bootstrap tags.

- `nix/_dockerfiles/versions/**/Dockerfile`  
  Renovate-managed "version intent" files (tag only, no digest).

- `nix/_dockerfiles/pins/**/Dockerfile`  
  Renovate-managed "pinned" files (tag + digest).

- `digests.json`  
  Final generated artifact consumed by Nix outputs.

- `nix/scripts/manage-images.py`  
  Script implementing generation/harvest logic.

- `.github/workflows/manage-images.yml`  
  Orchestrates generation, harvesting, commits, and PR creation.

- `renovate.json`  
  Defines how Renovate updates version and pin Dockerfiles.

- `.mergify.yml`  
  Auto-merges workflow and Renovate PRs via queue rules.

- `nix/oci-hashes.nix`  
  Exposes `digests.json` as flake output `ociHashes`.

---

## 3) Data Model

### `images.json` schema (per entry)

- `image`: fully-qualified image name (`docker.io/...`, `ghcr.io/...`)
- `platforms`: list like `linux/amd64`, `linux/arm64`
- `initialMajor`: bootstrap tags for major strategy
- `initialMajorMinor`: bootstrap tags for major-minor strategy
- `initialMajorMinorPatch`: bootstrap tags for full strategy

### Filesystem mapping used by script

- Image path segment: `/`, `:`, `.` replaced by `_`
- Platform path segment: `/` replaced by `_`
- Tag path segment for pins: `.`, `/` replaced by `_`

Example:
- Image `docker.io/nextcloud` -> `docker_io_nextcloud`
- Platform `linux/amd64` -> `linux_amd64`
- Tag `33.0` -> `33_0`

---

## 4) Workflow: `Manage OCI Images`

Defined in `.github/workflows/manage-images.yml`.

### Triggers (when it runs)

1. `push` to `main` when any of these change:
   - `images.json`
   - `nix/_dockerfiles/versions/**`
   - `nix/_dockerfiles/pins/**`
2. `workflow_dispatch` (manual run)
3. `schedule` every 6 hours (`0 */6 * * *`)

### Job-level guard

The `manage` job is skipped for `push` commits authored by `actions-user` to avoid loops, but still runs for schedule/manual events.

### Permissions

- `contents: write`
- `pull-requests: write`

### Step-by-step behavior and produced data

1. **Checkout**
   - Uses `actions/checkout@v6`
   - Token: `${{ secrets.PR_TOKEN || secrets.GITHUB_TOKEN }}`
   - `fetch-depth: 0`
   - **Output:** full git history in runner workspace.

2. **Install Nix**
   - Uses `cachix/install-nix-action@v31`
   - **Output:** Nix toolchain available for subsequent `nix build` / `nix run`.

3. **Build manage script**
   - Runs `nix build .#manage-images`
   - **Output:** validated runnable package for `manage-images`.

4. **Detect changed files** (`tj-actions/changed-files@v47`)
   - Buckets changes into `images`, `versions`, `pins`
   - **Output:** booleans like `images_any_changed`, `versions_any_changed`, `pins_any_changed`.

5. **Determine which generation steps to run**
   - `run_step1=true` when `images.json` changed, or schedule/manual
   - `run_step2=true` when step1 conditions or versions changed
   - `run_step3=true` when step2 conditions or pins changed
   - **Output:** `run_step1`, `run_step2`, `run_step3` in `$GITHUB_OUTPUT`.

6. **Configure Git identity**
   - Sets local name/email for commits
   - **Output:** git ready to commit generated files.

7. **Step 1: Generate version Dockerfiles** (conditional)
   - Command: `nix run .#manage-images -- generate-versions`
   - Script behavior:
     - Reads `images.json`
     - For each strategy (`major`, `major-minor`, `major-minor-patch`) uses first bootstrap tag
     - Creates missing files only in `nix/_dockerfiles/versions/.../Dockerfile`
     - Dockerfile line format: `FROM --platform=<platform> <image>:<tag>`
   - If files changed, commits:
     - `chore: generate version Dockerfiles from images.json`
   - **Produced data:** new/updated version-intent Dockerfiles.

8. **Step 2: Generate pin Dockerfiles** (conditional)
   - Command: `nix run .#manage-images -- generate-pins`
   - Script behavior:
     - Harvests tags from all existing version Dockerfiles
     - Also includes all bootstrap tags from `images.json`
     - Creates missing files only in `nix/_dockerfiles/pins/.../Dockerfile`
     - Initial line format (before Renovate digest update):
       - `FROM --platform=<platform> <image>:<tag>`
   - If files changed, commits:
     - `chore: generate pin Dockerfiles from version tags`
   - **Produced data:** complete pin candidates for each image/tag/platform.

9. **Step 3: Harvest digests to JSON** (conditional)
   - Command: `nix run .#manage-images -- harvest-digests`
   - Script behavior:
     - Scans all pin Dockerfiles
     - Parses `FROM` line and keeps only entries that include `@sha256:<64hex>`
     - Skips pin Dockerfiles that do not yet have digests
     - Writes sorted `digests.json` as:
       - `image -> tag -> platform -> "image:tag@sha256:digest"`
   - If changed, commits:
     - `chore: update digests.json with latest image references`
   - **Produced data:** canonical machine-consumable digest map.

10. **Check for changes vs `origin/main`**
    - `git diff --quiet HEAD origin/main`
    - **Output:** `changes=true/false`.

11. **Push and PR management** (only when changes exist)
    - Uses fixed branch: `update-oci-images`
    - Force-pushes branch
    - Creates or edits PR titled `chore: update OCI image references`
    - New PR labels: `update`, `digests`
    - **Produced data:** one continuously updated automation PR containing generated commits.

---

## 5) Renovate Configuration and Its Effects

Defined in `renovate.json`.

### For `nix/_dockerfiles/versions/**`

- Manager: `dockerfile`
- Digest updates disabled (`pinDigests: false`; digest/pinDigest update types disabled)
- Tag updates enabled with labels `dependencies`, `docker`, `tag-update`
- Path-specific constraints:
  - `versions/major/**`: minor/patch disabled -> major only
  - `versions/major-minor/**`: patch disabled -> major+minor
  - `versions/major-minor-patch/**`: major/minor/patch allowed

**Result:** Renovate moves version tags according to directory policy, never adds digests here.

### For `nix/_dockerfiles/pins/**`

- Manager: `dockerfile`
- `pinDigests: true` (always add/update digest)
- major/minor/patch updates disabled
- Labels include `dependencies`, `docker`, `digest-update`

**Result:** tag is stable in each pin file, Renovate updates only digest.

### Other Renovate behavior in this repo

- GitHub Actions dependency updates are enabled and labeled (`github-actions`)
- Nix lock maintenance enabled weekly before Monday 3am
- PR limits unbounded (`prConcurrentLimit: 0`, `prHourlyLimit: 0`)
- `autoApprove: true`, but `automerge: false` (merge handled by Mergify)

---

## 6) Mergify Automation

Defined in `.mergify.yml`.

- Auto-queues and merges:
  - OCI workflow PRs labeled `update` + `digests`
  - Renovate `tag-update` PRs
  - Renovate `digest-update` PRs
  - Renovate GitHub Actions and Nix updates

- Queue uses `rebase` merge method by default.

**Result:** end-to-end automation without manual merge for normal update traffic.

---

## 7) End-to-End Lifecycle

1. **Bootstrap / config change**
   - You edit `images.json`.
   - Workflow creates any missing version and pin Dockerfiles.
   - PR is opened/updated on `update-oci-images`.

2. **Tag movement (Renovate on versions)**
   - Renovate updates tags in `versions/**` according to strategy folder.
   - Push to `main` after merge triggers workflow.
   - Workflow creates any newly needed pin Dockerfiles for discovered tags.

3. **Digest pinning (Renovate on pins)**
   - Renovate updates `pins/**` Dockerfiles from `image:tag` to `image:tag@sha256:...`.
   - Push to `main` after merge triggers workflow.
   - Workflow harvests digests and updates `digests.json`.

4. **Consumer usage**
   - Nix flake output `ociHashes` reads `digests.json`.
   - Downstream systems consume pinned references reproducibly.

---

## 8) Reproducing This Technique in Another Repository

1. **Add source manifest**
   - Create `images.json` with image/platform/bootstrap-tag entries.

2. **Add generator/harvester script**
   - Implement commands equivalent to:
     - `generate-versions`
     - `generate-pins`
     - `harvest-digests`
   - Ensure deterministic JSON output and stable path sanitization.

3. **Define Dockerfile directory conventions**
   - `versions/{major|major-minor|major-minor-patch}/...`
   - `pins/.../<tag>/Dockerfile`

4. **Configure Renovate package rules**
   - `versions/**`: tag updates allowed, digests disabled
   - `pins/**`: tag updates disabled, digest pinning enabled
   - Strategy-specific update-type restrictions by subdirectory

5. **Create orchestration workflow**
   - Trigger on `push` (manifest/version/pin paths), schedule, and manual dispatch
   - Execute generation/harvest in stages with change-based conditions
   - Commit each stage’s outputs when changed
   - Push to a fixed automation branch and create/edit one PR

6. **Enable merge automation**
   - Add Mergify (or equivalent) rules to auto-merge approved bot PRs.

7. **(Forks) Add PR token secret**
   - Configure `PR_TOKEN` with repository `Contents: Read/Write` and `Pull requests: Read/Write` if default token permissions are insufficient for your PR flow.

8. **Expose output to consumers**
   - Publish `digests.json` (directly or via build system output) for downstream tooling.

---

## 9) Expected Artifacts at Each Stage (Quick Reference)

- After **generate-versions**: only `nix/_dockerfiles/versions/**` changes
- After **generate-pins**: only `nix/_dockerfiles/pins/**` changes
- After **harvest-digests**: only `digests.json` changes
- After PR step: branch `update-oci-images` updated, PR created/edited with labels `update`, `digests`

This separation is what makes the system observable, reproducible, and easy to debug.
