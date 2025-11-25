# request-vault-token

Requests a token from a given vault.

## Usage

Example usage:

```yaml
on:
  push: main

permissions: {}

jobs:
  check:
    runs-on: ubuntu-latest
    environment: vault-access

    steps:
      - name: Get Token
        id: get-token
        uses: saleor/saleor-internal-actions/request-vault-token@v1
        with:
          # Provides required inputs
          vault-url: ${{ secrets.VAULT_URL }}
          vault-jwt: ${{ secrets.VAULT_JWT }}

      - name: Checkout
        uses: <my-action>
        with:
          # Uses the token that was requested:
          token: ${{ steps.get-token.outputs.token }}
```
