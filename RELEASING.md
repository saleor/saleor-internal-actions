## Releasing

> [!NOTE]
> This repository follows the [Semantic Versioning].

To create a new release:

1. Change the version numbers in `.github/workflows/run-generate-sbom-and-check-licenses.yaml` (e.g., `@v1.0.0` -> `@v1.0.1`)
2. Open a pull request with the 1) changes
3. Once merged, create a release at https://github.com/saleor/saleor-internal-actions/releases/
4. Update the `v1` tag:

  ```
  git fetch --tags
  git checkout 1.0.1 # Use the version that you want to release
  git tag --force v1
  git push origin --force refs/tags/v1
  ```

[Semantic Versioning]: https://semver.org/
