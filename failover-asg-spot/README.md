# failover-asg-spot

In some cases, we may want to run a number of non-critical tasks as part of workers, e.g.: push notifications. To minimize cost, we want to utilize spot instances as much as possible. 

However, there are ~5 cases a week where AWS is running out of spot instances (the price spikes up to 10x higher) and we lose our spot instances bid for several hours. In order to maintain our availability, we will switch to on-demand instances until our spot instances are back.

![Pricing](https://raw.githubusercontent.com/freedomofkeima/aws-lambda-collections/master/failover-asg-spot/img/pricing.png)

All worker tasks are managed under ECS cluster and this script will do additional check to avoid scale-in before we have enough running instances in our ECS cluster.

By utilizing this script, we can maintain downtime for non-critical tasks around 10 minutes, compared to several hours due to spot instances loss.

## Deployment Steps

**Step 1**

Create a new Lambda function at AWS Lambda. In the code part, just simply copy the content of `handler.py`. In the role part, create a new role based on the value of `lambda-iam-role.json`. Specify `index.main` at the Handler part. For memory and timeout, we can specify the lowest memory (128 MB) and set the timeout to some reasonable value (~30s).

This script has the following parameters (specified in `handler.py`):

- REGION_NAME: AWS region name
- TARGETS - asg-on-demand-name: The name of on-demand ASG
- TARGETS - asg-spot-name: The name of spot ASG
- TARGETS - minimum-total-count: The minimum number of instances that should be running in ECS cluster
- TARGETS - minimum-on-demand-count: The minimum number of on-demand instances (if you decide to use some on-demand instances in combination of spot instances)
- TARGETS - ecs-cluster-name: The name of ECS cluster
- SLACK_WEBHOOK_URL: Webhook URL for Slack
- SLACK_CHANNEL: The name of Slack channel

**Step 2**

In the `Event sources` tab, click on "Add event source". Choose "CloudWatch Events - Schedule" as the source type. Specify `rate(10 minutes)` in order to execute this script every 10 minutes.

## Message Example (Slack)

```
AWS Watchers BOT [9:55 PM]  
Failover Instances Script
=============================================
Set desired capacity of test_cluster_on_demand (on-demand group) to 4
Number of running spot instances: 0
Number of running on-demand instances: 1 -> 4
Number of minimum on-demand instances: 1
Number of minimum total instances: 4
```
