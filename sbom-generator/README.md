# sbom-generator

Generates the [CycloneDX] SBOM of a given project, and fetches dependencies licenses using [`cdxgen`].


## Usage

### GitHub Action

```yaml
on:
  pull_request:
    types:
      - opened
      - synchronize
    paths:
      # Python Ecosystem
      - "**/pyproject.toml"
      - "**/setup.py"
      - "**/requirements*.txt"
      - "**/Pipfile.lock"
      - "**/poetry.lock"
      # JS/TS Ecosystem
      - "**/package.json"
      - "**/pnpm-lock.yaml"
      - "**/package-lock.json"

permissions:
  contents: read

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Analyze Licenses
        uses: saleor/saleor-internal-actions/sbom-generator@v1
        with:
          # Where to store the resulting SBOM file (default is ./sbom.json).
          sbom_path: ./sbom.json
          # The project to scan (default is ./).
          project_path: ./
          # The ecosystems to scan, scans all by default.
          #
          # See https://cyclonedx.github.io/cdxgen/#/PROJECT_TYPES for the supported
          # ecosystems ("Project Types" column).
          ecosystems: |
            python
            javascript
```

[`cdxgen`]: https://github.com/CycloneDX/cdxgen/
[CycloneDX]: https://cyclonedx.org/
