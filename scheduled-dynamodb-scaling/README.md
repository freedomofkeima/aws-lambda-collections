# scheduled-dynamodb-scaling

DynamoDB has a limitation of scaling down read/write throughput: 4 times a day. In this case, it's not easy to adjust DynamoDB throughput with dynamic approach.

However, there are a lot of cases where we can easily predict the behavior of DynamoDB throughput. For example, we may know that the peak time of our users is daily work time (MON-FRI), so we can adjust our throughput based on the given information.

Therefore, we might be interested to adjust throughput for several tables based on a specified schedule. e.g.:

```
[
    {
        "region-name": "ap-northeast-1",
        "table-name": "my-table-japan",
        "read-throughput": 5,
        "write-throughput": 5
    },
    {
        "region-name": "ap-southeast-1",
        "table-name": "my-table-singapore",
        "read-throughput": 5,
        "write-throughput": 5
    }
]
```

And set the cron schedule to, e.g., `cron(0 0 ? * MON-FRI *)`.

## Deployment Steps

**Step 1**

In CloudWatch, go to "Rules" (under "Events") and create a new rule. This rule will be used as your Lambda scheduler and input.

![Rule](https://raw.githubusercontent.com/freedomofkeima/aws-lambda-collections/master/scheduled-dynamodb-scaling/img/rule.png)

**Step 2**

Create a new Lambda function at AWS Lambda. In the code part, just simply copy the content of `handler.py`. In the role part, create a new role based on the value of `lambda-iam-role.json`. Specify `index.main` at the Handler part. For memory and timeout, we can specify the lowest memory (128 MB) and set the timeout to some reasonable value (~60s).

This script has the following parameters (specified in `handler.py`):

- SLACK_WEBHOOK_URL: Webhook URL for Slack
- SLACK_CHANNEL: The name of Slack channel

**Step 3**

In the `Event sources` tab, click on "Add event source". Choose "CloudWatch Events - Schedule" as the source type. Choose the rule which has been created from **Step 1**.

## Message Example (Slack)

```
List of scheduled DynamoDB throughput operations
=============================================
Throughput for my-table-japan (R: 1 -> 5, W: 1 -> 5)
Throughput for my-table-singapore is not changed (R/W: 5/5)
```
