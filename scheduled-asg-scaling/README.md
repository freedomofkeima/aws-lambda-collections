# scheduled-asg-scaling

Auto Scaling Group has a native feature of [Scheduled Scaling](http://docs.aws.amazon.com/autoscaling/latest/userguide/schedule_time.html). However, in some cases, we want to have more flexibility and centralize capacity control for a lot of ASGs in one configuration.

For example, we have two clusters which are a part of blue-green deployment (1/0 or 0/1). If the current release is in "blue" cluster, we only need to auto-scale the "blue" cluster in the specified cron time.

The configuration input for our Lambda function should be specified as the following:

```
[
    {
        "region-name": "ap-northeast-1",
        "asg-name": [
            "asg-cluster-a",
            "asg-cluster-b"
        ],
        "type": "max",
        "desired-capacity": 4
    },
    {
        "region-name": "ap-northeast-1",
        "asg-name": [
            "asg-cluster-c",
            "asg-cluster-d",
            "asg-cluster-e"
        ],
        "type": "all",
        "desired-capacity": 2
    }
]
```

There are 2 kind of types: `max` and `all`.

`max` is used if we have several mutual exclusive clusters (e.g.: blue-green deployment with 2 set of clusters). In this case, the algorithm will choose **exactly one** cluster with highest **current desired capacity**. In normal cases, the other cluster should have 0 value because the cluster is in unused condition.

`all` is used if we want to set all specified ASG to the same `desired-capacity`.

Finally, we need to set the cron schedule (Scheduled Event) to the value that we want, e.g., `cron(0 0 ? * MON-FRI *)`.


## Deployment Steps

**Step 1**

In CloudWatch, go to "Rules" (under "Events") and create a new rule. This rule will be used as your Lambda scheduler and input.

![Rule](https://raw.githubusercontent.com/freedomofkeima/aws-lambda-collections/master/scheduled-asg-scaling/img/rule.png)

**Step 2**

Create a new Lambda function at AWS Lambda. In the code part, just simply copy the content of `handler.py`. In the role part, create a new role based on the value of `lambda-iam-role.json`. Specify `index.main` at the Handler part. For memory and timeout, we can specify the lowest memory (128 MB) and set the timeout to some reasonable value (~60s).

This script has the following parameters (specified in `handler.py`):

- SLACK_WEBHOOK_URL: Webhook URL for Slack
- SLACK_CHANNEL: The name of Slack channel

**Step 3**

In the `Event sources` tab, click on "Add event source". Choose "CloudWatch Events - Schedule" as the source type. Choose the rule which has been created from **Step 1**.


## Message Example (Slack)
```

List of scheduled ASG desired capacity scaling operations
=============================================
tokyo_cluster_0, tokyo_cluster_1:
Set DesiredCapacity of tokyo_cluster_1 from 2 to 1

singapore_cluster_0, singapore_cluster_1:
Set DesiredCapacity of singapore_cluster_1 from 2 to 1
```
