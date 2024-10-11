# grant-license-checker

An action that generates a report of licenses used by main and transient dependencies,
and checks for compliance issues using [grant](https://github.com/anchore/grant).

## Example Output

<table>
    <tr>
        <th width='200px'>License Name</th>
        <th>Package Count</th>
<th>Packages</th>    </tr>
    <tr>
        <td>PSF-2.0</td>
        <td>1</td>
            <td>
                <details>
                    <summary>Packages</summary>
                    <ul>
                        <li>typing-extensions</li>
                    </ul>
                </details>
            </td>
    </tr>
    <tr>
        <td>0BSD</td>
        <td>4</td>
            <td>
                <details>
                    <summary>Packages</summary>
                    <ul>
                        <li>colorama</li>
                        <li>Jinja2</li>
                        <li>MarkupSafe</li>
                        <li>packaging</li>
                    </ul>
                </details>
            </td>
    </tr>
    <tr>
        <td>MIT</td>
        <td>6</td>
            <td>
                <details>
                    <summary>Packages</summary>
                    <ul>
                        <li>annotated-types</li>
                        <li>iniconfig</li>
                        <li>pluggy</li>
                        <li>pydantic</li>
                        <li>pydantic-core</li>
                        <li>pytest</li>
                    </ul>
                </details>
            </td>
    </tr>
</table>

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
        id: analyze-licenses
        uses: saleor/saleor-internal-actions/grant-license-checker@v1
        with:
          # Needs to be a SBOM that contains license information (SPDX, CycloneDX,
          # and Syft formats are supported).
          # You can use 'saleor/saleor-internal-actions/sbom-generator' to generate such SBOMs.
          sbom_path: ./sbom.json
          # See https://cyclonedx.github.io/cdxgen/#/PROJECT_TYPES for the supported
          # ecosystems ("Project Types" column).
          ecosystems: |
            python
            javascript
          # YAML rules for grant.
          rules: |
            - pattern: "BSD-*"
              name: "allow-bsd"
              mode: "allow"
            - pattern: "*"
              name: "default-deny-all"
              mode: "deny"
              reason: "All licenses need to be explicitly approved (allow-list)"

      - name: Check Result
        env:
          CONCLUSION: ${{ steps.analyze-licenses.outputs.check_conclusion }}
        run: |
          if [ "$CONCLUSION" == fail ]; then
            echo "Found license violations!" >&2
            exit 1
          fi
          echo "License check passed!" >&2
```

### Reusable GitHub Workflow

```yaml
name: Check Licenses
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

jobs:
  default:
    permissions:
      contents: read
      pull-requests: write
    uses: saleor/saleor-internal-actions/.github/workflows/run-license-check.yaml@v1
```

### CLI

Usage:

```
usage: grant-summarize [-h] -i INPUT [-l] [-m MAX_PACKAGES] [-f {html,tty}] [-o OUTPUT] [-v VERBOSE | -D DEBUG]

This command summarizes a grant JSON output with human friendly formats. Such as: - HTML table (GitHub Markdown-compatible), - TTY plaintext.

options:
  -h, --help            show this help message and exit
  -v VERBOSE, --verbose VERBOSE
                        Enable verbose logging
  -D DEBUG, --debug DEBUG
                        Enable debug logging

Input Preferences:
  -i INPUT, --input INPUT
                        The grant JSON output file

Output Preferences:
  -l, --list-packages   Whether to include the package list in the output.
  -m MAX_PACKAGES, --max-packages MAX_PACKAGES
                        The maximum number of packages to include in the output per license. A value too large can potentially not fit inside GitHub comments.
  -f {html,tty}, --format {html,tty}
                        The output format, one of: 'text' (logs friendly), 'html' (markdown friendly)
  -o OUTPUT, --output OUTPUT
                        The path to the output the result. Defaults to stdout.
```

End to end example:

1. `cd <path to project>`
2. Generate the SBOM:
   ```
   docker run \
     --rm \
     -v "$(pwd):/app:rw" \
     --env FETCH_LICENSE=true \
     -t ghcr.io/cyclonedx/cdxgen:v10.9.5 \
     -r /app -o /app/bom.json --profile license-compliance -t npm -t python
   ```
3. Generate the `grant` report:
   ```
   grant check ./bom.json -o json > ./grant.json
   ```
4. Generate the summary:
   ```
   grant-summarize -i grant.json
   ```

## Development

This project takes a `grant check` JSON report as input and renders it.

### Project Structure

- `cmd/`
  - Module where commands should be defined at;
  - When adding a new command, add it in `pyproject.toml` to ensure it is installed into the `PATH` (`PATH` is updated on `poetry install`).
- `renderers/`
  - Module containing rendering templates and logics;
  - When adding a new renderer, register it inside `__init__.py`, it will be automatically available for use via `--format=<name>`.
- `tests/fixtures/`
  - Contains test data that can also be used during the project's development;
  - `sample-sbom-v1.5.json` - a basic CycloneDX SBOM file (https://cyclonedx.org/docs/1.5/json/).
    Can be used against `grant`, e.g `grant check ./bom.json -o table --show-packages`;
  - `sample-grant-report.json` - a basic JSON report generated by `grant check`.
