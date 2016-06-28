# running-instances-monitor

The main purpose of this script is to keep all of your running instances across multiple regions keep in-check.

By utilizing this script, we can ensure that all running instances are actually needed. And, we can also ensure that no one has escalated malicious privilege and launch some instances in our account.

## Deployment Steps

**Step 1**

Create a new Lambda function at AWS Lambda. In the code part, just simply copy the content of `handler.py`. In the role part, create a new role based on the value of `lambda-iam-role.json`. Specify `index.main` at the Handler part. For memory and timeout, we can specify the lowest memory (128 MB) and set the timeout to some reasonable value (~60s).

This script has the following parameters (specified in `handler.py`):

- SLACK_WEBHOOK_URL: Webhook URL for Slack
- SLACK_CHANNEL: The name of Slack channel

**Step 2**

In the `Event sources` tab, click on "Add event source". Choose "CloudWatch Events - Schedule" as the source type. Specify `0 13 ? * * *` in order to execute this script everyday at 13:00 UTC.

## Message Example (Slack)

```
List of running instances
=============================================
Running at ap-northeast-1
=============================================
i-12345678,Instance Name 1 (m3.medium)
i-23456789,Instance Name 2 (m3.medium)
=============================================
Running at ap-southeast-1
=============================================
i-34567890,Instance Name 3 (m3.medium)
```
