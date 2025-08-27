## Upgrading CycloneDX (cdxgen)

1. Update references to the version to upgrade, e.g., if current version is `11.6.0`,
   then search & replace that version number.
2. Test the ability to generate SBOM correctly using the following (replace the cdxgen version):
   ```
   $ apt install -y nodejs npm jq curl git
   $ ./scripts/test-cdxgen-support.sh --cdxgen-version v11.6.0
   ```
3. Run the following in the root directory of this project:
   ```
   $ ./grant-license-checker/scripts/download-grant.sh
   $ export PATH="$PATH:$PWD/.grant"
   $ ./grant-license-checker/grant_license_checker/tests/fixtures/generate.sh
   ```
4. Run `pytest` in `../grant-license-checker/grant_license_checker/`
