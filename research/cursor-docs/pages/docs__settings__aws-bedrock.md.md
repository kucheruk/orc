# AWS Bedrock

Route AI requests through your AWS Bedrock account instead of Cursor's model providers. This lets your team use existing AWS credits and keep requests within your AWS infrastructure.

![AWS Bedrock settings in Cursor](/docs-static/images/settings/aws-bedrock-settings.png)

## IAM role setup (recommended)

The recommended approach is to create an IAM role that grants Cursor permission to invoke Bedrock models on your behalf.

### Step 1: Create the IAM role

Create a new IAM role with the following trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::289469326074:role/roleAssumer"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "<your-external-id>"
        }
      }
    }
  ]
}
```

Replace `<your-external-id>` with the External ID shown in your Cursor settings. This ID is generated after you first validate your Bedrock configuration and prevents the [confused deputy problem](https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html).

### Step 2: Attach permissions

Attach a policy that grants access to the Bedrock models you want to use:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.*",
        "arn:aws:bedrock:*::foundation-model/us.anthropic.*"
      ]
    }
  ]
}
```

Adjust the resource ARNs to match the specific models and regions you want to allow.

### Step 3: Enable models in Bedrock

Before using a model, you must enable it in the AWS Bedrock console:

1. Open the [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/)
2. Navigate to **Model access** in the left sidebar
3. Click **Manage model access**
4. Select the models you want to use
5. Click **Save changes**

### Step 4: Configure in Cursor

1. Go to `Cursor Settings` > `Models`
2. Find the **Bedrock IAM Role** section
3. Enter your credentials:

| Setting              | Description                                                                  |
| -------------------- | ---------------------------------------------------------------------------- |
| **AWS IAM Role ARN** | Your IAM role ARN (e.g., `arn:aws:iam::123456789012:role/CursorBedrockRole`) |
| **AWS Region**       | The AWS region where Bedrock is enabled (e.g., `us-east-1`)                  |
| **Test Model ID**    | A model to test connectivity                                                 |

4. Click **Validate & Save** to test the connection

## External ID

After validating your Bedrock configuration, Cursor generates a unique External ID. Add this to your IAM role's trust policy under the `Condition` section to enable secure cross-account access.

The External ID prevents unauthorized access to your AWS resources. Copy the ID from your Cursor settings and update your trust policy accordingly.

## Using access keys

Alternatively, you can use AWS access keys instead of an IAM role. Enter your AWS Access Key ID and Secret Access Key in the Cursor settings. This approach is simpler but less secure than using IAM roles.

## Troubleshooting

### Validation fails with access denied

- Verify the IAM role ARN is correct
- Check that the trust policy includes Cursor's cross-account ARN (`arn:aws:iam::289469326074:role/roleAssumer`)
- Confirm the External ID matches exactly
- Ensure the test model is enabled in Bedrock

### Model not found

- Enable the model in the AWS Bedrock console
- Verify the model ID format matches your region (some use `us.anthropic.*` prefix)
- Check that your IAM policy includes the model's ARN

### Region errors

- Confirm Bedrock is available in your selected region
- Verify the model is enabled in that specific region
- Some models are only available in certain regions

## Related

- [API Keys](https://cursor.com/docs/settings/api-keys.md) - Configure other model providers
- [Models](https://cursor.com/docs/models.md) - Overview of available models in Cursor


---

## Sitemap

[Overview of all docs pages](/llms.txt)
