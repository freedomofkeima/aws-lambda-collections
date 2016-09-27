# scheduled-ecs-scaling

Sometimes, we want not only to auto-scale our ASG clusters, but also our ECS tasks based on specified time / specific rule.
 
The configuration input for our Lambda function should be specified as the following:

```
[
    {
        "region-name": "ap-northeast-1",
        "cluster-name": "ecs-test-cluster",
        "service-name": "ecs-test-service",
        "desired-count": 4
    }
]
```

## Deployment Steps


**Step 1**

In CloudWatch, go to "Rules" (under "Events") and create a new rule. This rule will be used as your Lambda scheduler and input.

![Rule](https://raw.githubusercontent.com/freedomofkeima/aws-lambda-collections/master/scheduled-ecs-scaling/img/rule.png)

**Step 2**

Create a new Lambda function at AWS Lambda. In the code part, just simply copy the content of `handler.py`. In the role part, create a new role based on the value of `lambda-iam-role.json`. Specify `index.main` at the Handler part. For memory and timeout, we can specify the lowest memory (128 MB) and set the timeout to some reasonable value (~60s).

This script has the following parameters (specified in `handler.py`):

- SLACK_WEBHOOK_URL: Webhook URL for Slack
- SLACK_CHANNEL: The name of Slack channel

**Step 3**

In the `Event sources` tab, click on "Add event source". Choose "CloudWatch Events - Schedule" as the source type. Choose the rule which has been created from **Step 1**.


## Message Example (Slack)
```

```
