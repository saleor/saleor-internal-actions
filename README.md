# saleor-internal-actions

This is a collection of GitHub Actions created and used by Saleor internally.

> [!WARNING]
> This project is solely intended for internal use within the Saleor organization.
> It is provided as is, breaking changes may be published without notice, and may not be compatible for specific use cases.

## Actions

| Name                                           | Description                                                       |
| ---------------------------------------------- | ----------------------------------------------------------------- |
| [sbom-generator](sbom-generator)               | Generates a CycloneDX SBOM with license fetching enabled.         |
| [grant-license-checker](grant-license-checker) | Generates a license usage report of a given SBOM using [`grant`]. |
| [request-vault-token](request-vault-token)     | Requests a token from a given vault.                              |

## Reusable Workflows

| Name                                                                                           | Description                                                                                                                                                               |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [run-license-check.yaml](.github/workflows/run-license-check.yaml)                             | Summarizes the list of licenses as a pull request comment (by generating an SBOM.)                                                                                        |
| [build-push-image-multi-platform.yaml](.github/workflows/build-push-image-multi-platform.yaml) | Blazing fast building for multi-arch OCI images (ARM64 and AMD64 only). See [documentation](/.github/workflows/build-push-image-multi-platform.md) for usage information. |

## Development

Refer to [CONTRIBUTING.md](CONTRIBUTING.md).

[`grant`]: https://github.com/anchore/grant
