# Notify Slack

> [!WARNING]
> This workflow is only intended for internal use within the Saleor organization.
> It is provided as is and may not fit your use-case, we do not provide support
> for it and breaking changes may occur without notice.

[notify-slack.yaml](./notify-slack.yaml) is a reusable GitHub Workflow for sending
notifications to Slack using an [incoming webhook]. It wraps the
[slackapi/slack-github-action] (v2) to provide a consistent interface across all
Saleor workflows.

The message includes a colored sidebar based on status (green for success, red for
failure, grey for other), and a body with the author, status, and a link to the
workflow run.

### Message format - depends on the inputs:

1. When `type: build` is provided:
    > [repo-name]() | Finished build of **{ref}**
    >
    > Author: **username**
    >
    > Workflow: [workflow-name]()
    >
    > Status: **status**
    >
    > [View run logs]()

2. When `type: deployment` is provided:
    > [repo-name]() | **{product}** | Finished deployment of **{ref}** to **{environment}**
    >
    > Author: **username**
    >
    > Workflow: [workflow-name]()
    >
    > Status: **status**
    >
    > [View run logs]()

3. When `custom_title:` is provided:
    > [repo-name]() | {your custom title}
    >
    > Author: **username**
    >
    > Workflow: [workflow-name]()
    >
    > Status: **status**
    >
    > [View run logs]()

## Usage

### Inputs

| Input name | Description                                                                  | Type   | Default | Notes                                            |
| ---------- | ---------------------------------------------------------------------------- | ------ | ------- | ------------------------------------------------ |
| `custom_title` | Custom title for the notification. Supports Slack mrkdwn.                | string | `""`    | If provided, `type` and `ref` are not required.  |
| `type`     | The type of notification: `build` or `deployment`.                           | string | `""`    | Required if `custom_title` is not provided.             |
| `ref`      | The git ref (branch, tag, or SHA) that was built or deployed.                | string | `""`    | Required if `custom_title` is not provided.             |
| `status`   | The outcome of the workflow. Controls sidebar color (green=success, red=failure, grey=other). | string | -       | **Required**.                                    |
| `product`  | The product being deployed (e.g., `keycloak`, `saleor-multitenant`).         | string | `""`    | Required when `type` is `deployment`.            |
| `environment` | The target environment (e.g., `prod`, `staging`, `v322-staging`).         | string | `""`    | Required when `type` is `deployment`.            |

### Secrets

| Secret name         | Description                     | Notes                                                                                                   |
| ------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `slack-webhook-url` | A Slack incoming webhook URL.   | **Required**. Our "Cloud Deployments" app webhooks can be found [here][cloud-deployments-app-webhooks]. |

### Outputs

| Output name | Description                                           |
| ----------- | ----------------------------------------------------- |
| `ok`        | Whether the request completed without errors.         |
| `response`  | A JSON stringified version of the Slack API response. |

## Examples

### Build notification

```yaml
name: Build
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - run: make build

  notify:
    needs: build
    if: ${{ always() }}
    uses: saleor/saleor-internal-actions/.github/workflows/notify-slack.yaml@main
    with:
      type: build
      ref: ${{ github.ref_name }}
      status: ${{ needs.build.result }}
    secrets:
      slack-webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Deployment notification

```yaml
name: Deploy
on:
  workflow_dispatch:
    inputs:
      product:
        required: true
        type: string
      environment:
        required: true
        type: string

jobs:
  deploy:
    runs-on: ubuntu-24.04
    steps:
      - run: echo "Deploying..."

  notify:
    needs: deploy
    if: ${{ always() }}
    uses: saleor/saleor-internal-actions/.github/workflows/notify-slack.yaml@main
    with:
      type: deployment
      ref: ${{ github.ref_name }}
      product: ${{ inputs.product }}
      environment: ${{ inputs.environment }}
      status: ${{ needs.deploy.result }}
    secrets:
      slack-webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Custom title notification

```yaml
name: Custom Notification
on:
  workflow_dispatch:

jobs:
  task:
    runs-on: ubuntu-24.04
    steps:
      - run: echo "Doing something..."

  notify:
    needs: task
    if: ${{ always() }}
    uses: saleor/saleor-internal-actions/.github/workflows/notify-slack.yaml@main
    with:
      custom_title: "*Custom task* completed"
      status: ${{ needs.task.result }}
    secrets:
      slack-webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

[incoming webhook]: https://api.slack.com/messaging/webhooks
[slackapi/slack-github-action]: https://github.com/slackapi/slack-github-action
[cloud-deployments-app-webhooks]: https://api.slack.com/apps/A0A56MD0DHS/incoming-webhooks?
