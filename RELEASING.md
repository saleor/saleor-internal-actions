# Releasing

> [!NOTE]
> This repository follows the [Semantic Versioning].

To create a new release:

1. Change the version numbers for **every** action starting with the name
   `saleor/saleor-internal-actions/` in `.github/workflows/run-generate-sbom-and-check-licenses.yaml`

   For example:

   ```diff
   - @49a069ae9731cfccf3a1033fe1da4e3da84f4f2a # v1.11.0
   + @166077722d8ab62468ac7def8a2b59594834ee04 # v1.12.0
   ```

2. Commit the changes
3. Open a pull request with the 1) changes
4. Create a release at https://github.com/saleor/saleor-internal-actions/releases/

   ⚠️ Once you hit the publish button, you will no longer be able to mutate the tag.

[Semantic Versioning]: https://semver.org/
