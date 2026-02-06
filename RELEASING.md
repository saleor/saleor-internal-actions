# Releasing

> [!NOTE]
> This repository follows the [Semantic Versioning].

To create a new release:

1. Change the version numbers in `.github/workflows/run-generate-sbom-and-check-licenses.yaml` (e.g., `@v1.0.0` -> `@v1.0.1`)
2. Commit the changes
3. Create a tag:
   ```
   $ git tag -s -m v1.0.1 v1.0.1
   $ git push --tags
   ```
4. Open a pull request with the 1) changes
5. Once merged, update the v1.0.1 tag's commit SHA:
   ```
   $ git checkout main
   $ git pull
   $ git tag --force -s v1.0.1
   $ git push origin --force refs/tags/v1.0.1
   ```
7. Update the `v1` tag:

   ```
   git fetch --tags
   git checkout v1.0.1 # Use the version that you want to release
   git tag --force v1
   git push origin --force refs/tags/v1
   ```
8. Create a release at https://github.com/saleor/saleor-internal-actions/releases/

   ⚠️ Once you hit the publish button, you will no longer be able to mutate the tag.
   Thus make sure you performed step 5) correctly.

[Semantic Versioning]: https://semver.org/
