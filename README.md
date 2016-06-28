# aws-lambda-collections

This repository contains several AWS Lambda codes written in Python to maintain and monitor running infrastructures in AWS and propagate some information to developers via Slack.

## Contents

Another README is provided in each respective directories. This repository contains the following modules:

- failover-asg-spot: Failover script between spot and on-demand ASG instances with ECS cluster checking
- running-instances-monitor: List all running instances in AWS infrastructure
- scheduled-asg-scaling: Scale-in and Scale-out ASG during specified heavy workload time (cron)

## License

MIT License.

Last Updated: June 28, 2016
