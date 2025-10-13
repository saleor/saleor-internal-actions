# Multi-Platform Build & Push for Container Images

> [!WARNING]
> This workflow is only intended for internal use within the Saleor organization.
> It is provided as is and may not fit your use-case, we do not provide support
> for it and breaking changes may occur without notice.

[build-push-image-multi-platform.yaml](./build-push-image-multi-platform.yaml) is a
reusable GitHub Workflow that builds and publishes container images for ARM64 and x64
(AMD64) architectures.

It executes two independent runners to build the two architectures natively on the host
(ARM64 and x64), and then merges the resulting platform‑specific images into a [image index]
(which tells `docker` CLI and other container runtimes which image to pull for ARM64,
and which one for AMD64.)

Key features:

- Native builds on the host (no QEMU emulation).
- Possibility of using custom GitHub runners (e.g., switching from 2 cores to 4 cores,
  or using self-hosted runners, or upgrading/downgrading the Ubuntu version, …)
- Utilizes GitHub cache to further optimize build time.
- Automatically handles login for the chosen registries (currently only GHCR and AWS ECR
  are supported.)

Comparison against the legacy approach:

| Metric                      | Legacy Approach                | This Workflow                                       |
| --------------------------- | ------------------------------ | --------------------------------------------------- |
| Runner Settings             | 1 runner, 4 cores, Linux, QEMU | 2 runners (parallel build), 2 cores, Linux, no QEMU |
| Build duration (multi‑arch) | 40 to 60 minutes               | 2 minutes                                           |
| Cost per build              | $0.64 to $0.96/build           | ~$0.032 (2 + 2 minutes, parallel build)             |
| CI pipeline runtime         | 40~60 min                      | ~2 min                                              |

## Usage

> [!NOTE]
> The workflow always builds both architectures, the caller cannot an architecture
> (e.g., **only** building ARM64 isn't supported).

### Inputs

**Checkout behavior:**

| Input name            | Description                                                              | Type    | Default   | Notes                                                                                                                |
| --------------------- | ------------------------------------------------------------------------ | ------- | --------- | -------------------------------------------------------------------------------------------------------------------- |
| `checkout-ref`        | Git reference (branch, tag or SHA) to checkout in the source repository. | string  | -         | Uses the defaults to the reference or SHA for the GitHub event (e.g., the commit that was pushed for `push` events.) |
| `checkout-use-vault`  | Whether to use the vault to fetch repositories.                          | boolean | `false`   | Only required when using git submodules that point to private repositories.                                          |
| `checkout-submodules` | Whether to checkout git submodules.                                      | string  | `"false"` | Refer to the documentation for the `submodules` field in https://github.com/actions/checkout/.                       |

**GitHub Runner Settings:**

| Input name           | Description                                              | Type   | Default          | Notes                                                                                                                                             |
| -------------------- | -------------------------------------------------------- | ------ | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `amd64-runner-image` | The GitHub runner to use for **x64** image building.     | string | ubuntu-24.04     | Can be a self-hosted runner, a custom, or GitHub-hosted runner (list: https://docs.github.com/en/actions/reference/runners/github-hosted-runners) |
| `arm64-runner-image` | The GitHub runner to use for **aarch64** image building. | string | ubuntu-24.04-arm | Can be a self-hosted runner, a custom, or GitHub-hosted runner (list: https://docs.github.com/en/actions/reference/runners/github-hosted-runners) |

**Build Settings**:

| Input name            | Description                                                                                                                    | Type   | Default | Notes                                                                |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------ | ------- | -------------------------------------------------------------------- |
| `oci-full-repository` | Fully‑qualified OCI registry URI (including registry host, namespace and image name), e.g., `oci.example.com/acme/my-project`. | string | –       | **Required** – the _target_ registry where the image will be pushed. |
| `tags`                | Whitespace-separated list of tags to apply to the final image (e.g. `ghcr.io/org/img:latest ghcr.io/org/img:v1`).              | string | –       | **Required**.                                                        |
| `build-args`          | List of `--build-arg` arguments to pass to the builder.                                                                        | string | -       | See example below.                                                   |

<details>

<summary>Example usage for `tags` and `build-args`</summary>

```yaml
# […]
uses: saleor/saleor-build-workflow/.github/workflows/build.yaml@main
with:
tags: |
  oci.example.com/acme/my-project:v1.0.0
  oci.example.com/acme/my-project:latest
build-args: |
  MY_ARG1=foo
  MY_ARG2=bar
```

</details>

**GHCR Settings:**

| Input name    | Description                                                 | Type    | Default | Notes |
| ------------- | ----------------------------------------------------------- | ------- | ------- | ----- |
| `enable-ghcr` | Whether to log in to GitHub Container Registry (`ghcr.io`). | boolean | `false` |       |

**ECR Settings:**

| Input name               | Description                                                                           | Type    | Default | Notes                                                      |
| ------------------------ | ------------------------------------------------------------------------------------- | ------- | ------- | ---------------------------------------------------------- |
| `enable-aws-ecr`         | Whether to log in to Amazon ECR.                                                      | boolean | `false` |                                                            |
| `aws-ecr-region`         | AWS region for the ECR registry.                                                      | string  | –       |                                                            |
| `aws-ecr-role-to-assume` | ARN of the IAM role to assume for cross‑account ECR access.                           | string  | –       | **:warning: Passed as a secret**, see [example](#aws-ecr). |
| `aws-ecr-registries`     | Comma‑separated list of ECR registry account IDs (e.g., `123456789012,123456789013`). | string  | –       | **:warning: Passed as a secret**, see [example](#aws-ecr). |

**Outputs** (exposed by the `merge-digests` job)

| Output name | Description                                                                                                       |
| ----------- | ----------------------------------------------------------------------------------------------------------------- |
| `digest`    | SHA‑256 digest of the final multi‑arch image that was pushed to the target registry, see below for how to use it. |

<details>
<summary>How to use the <code>digest</code> output</summary>

The workflow exposes the final digest through the `digest` output, then other jobs
can reference it for further steps (e.g., tests, kubernetes deployment, …)

For example, you could run `pytest` on the image like so:

```yaml
name: Deploy Main
on:
  # NOTE: any trigger is supported (pull_request, release, …)
  push: [main]

jobs:
  build_image:
    uses: saleor/saleor-build-workflow/.github/workflows/build.yaml@main
    with:
      oci-full-repository: "ghcr.io/saleor/saleor"
      tags: |
        ghcr.io/saleor/saleor:latest
        ghcr.io/saleor/saleor:1.2.4
      enable-ghcr: true

  pytest:
    runs-on: ubuntu-24.04
    needs: [build_image]
    timeout-minutes: 5

    env:
      IMAGE: ghcr.io/saleor/saleor@${{ needs.build_push.outputs.digest }}

    steps:
      - uses: actions/checkout@v5

      - name: Run Pytest
        run: |
          docker run --rm "$IMAGE" pytest
```

</details>

### AWS ECR

```yaml
name: Deploy Main
on:
  # NOTE: any trigger is supported (pull_request, release, …)
  push: [main]

jobs:
  build-image:
    uses: saleor/saleor-build-workflow/.github/workflows/build.yaml@main
    with:
      oci-full-repository: "123456789012.dkr.ecr.us-east-1.amazonaws.com/saleor/saleor"
      tags: |
        123456789012.dkr.ecr.us-east-1.amazonaws.com/saleor/saleor:latest
        123456789012.dkr.ecr.us-east-1.amazonaws.com/saleor/saleor:1.0.0
      enable-ghcr: false
      enable-aws-ecr: true
    secrets:
      aws-ecr-role-to-assume: arn:aws:iam::1234567890:role/my-role
      aws-ecr-registries: "1234567890" # AWS Account ID
      aws-ecr-region: "us-east-1"
```

### GitHub Container Registry (GHCR)

```yaml
name: Deploy Main
on:
  # NOTE: any trigger is supported (pull_request, release, …)
  push: [main]

jobs:
  push-ghcr:
    uses: saleor/saleor-build-workflow/.github/workflows/build.yaml@main
    with:
      oci-full-repository: "ghcr.io/saleor/saleor"
      tags: |
        ghcr.io/saleor/saleor:latest
        ghcr.io/saleor/saleor:1.2.4
      enable-ghcr: true
```

## Architecture

The workflow consists of two phases:

1. Parallel builds (job called "build"):
   - It runs two runners in parallel that build the image for the ARM64 and x64/AMD64 platforms respectively.
   - It takes care of login & pushing to OCI registries (AWS ECR and/or GHCR).
   - It does NOT put any image tag yet, only pushes anonymous images (i.e., no tags, only a manifest ID such as
     `sha256:3b03f1169a35f1d492a786f588660170c59a8e71e8e69b4c97c66278c0e08431`), this is important in order to be
     able to create a [image index] (explained below)
2. Manifest merge (job "merge-digests"):
   - It executes on a single runner once all parallel builds succeed (thus waits for the build to finish).
   - It pulls the per‑platform digests (using `actions/download-artifact`).
   - It then creates a manifest list ([image index]) and pushes it to the target repository.
     The manifest list/image index will look like this (which is used by docker and other runtimes
     to determine which digest to pull from the registry such as ECR or GHCR):

     ```json
     {
       "schemaVersion": 2,
       "mediaType": "application/vnd.oci.image.index.v1+json",
       "manifests": [
         {
           "mediaType": "application/vnd.oci.image.manifest.v1+json",
           "size": 1234,
           "digest": "sha256:cc292b92ce7f10f2e4f727ecdf4b12528127c51b6ddf6058e213674603190d06",
           "platform": {
             "architecture": "amd64",
             "os": "linux"
           }
         },
         {
           "mediaType": "application/vnd.oci.image.manifest.v1+json",
           "size": 1234,
           "digest": "sha256:5bb21ac469b5e7df4e17899d4aae0adfb430f0f0b336a2242ef1a22d25bd2e53",
           "platform": {
             "architecture": "arm64",
             "os": "linux"
           }
         }
       ]
     }
     ```

   - Finally, it exposes the final image digest as a GitHub output (`digest`).

[image index]: https://github.com/opencontainers/image-spec/blob/6519a62d628ec31b5da156de745b516d8850c8e3/image-index.md
