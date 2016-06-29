#!/usr/bin/env python
# NOTE 1: Re-failover from on-demand to spot will be done if all desired ECS tasks are currently running
# NOTE 2: The maximum number of spot instances is taken from its DesiredCapacity
# WARNING: You cannot increase DesiredCapacity of on-demand from the console without changing this script,
#          however, you can increase DesiredCapacity of spot instances from the console and if it fails,
#          this script will start on-demand instead of spot instances
#
import boto3
import json
from urllib2 import Request, urlopen, URLError, HTTPError

# FILL THESE REQUIRED VARIABLES
REGION_NAME = "ap-northeast-1"
TARGETS = [
    {
        "asg-on-demand-name": "your_asg_on_demand_name",
        "asg-spot-name": "your_asg_spot_name",
        "minimum-total-count": 4, # Not strict, it's possible to have more spot instances
        "minimum-on-demand-count": 1, # To ensure the minimum of running on-demand instances
        "ecs-cluster-name": "your_ecs_joined_cluster_name" # Target ECS cluster for checking
    }
]
SLACK_WEBHOOK_URL = "YOUR_SLACK_WEBHOOK"  # Slack is optional (set it to None)
SLACK_CHANNEL = "YOUR_SLACK_CHANNEL"  # Slack is optional (set it to None)


def main(event, context):
    autoscaling_client = BotoClientFacade("autoscaling", REGION_NAME)
    ecs_client = BotoClientFacade("ecs", REGION_NAME)
    groups = retrieve_asg_groups(autoscaling_client)
    # Iterate through all set of ASG targets
    for target in TARGETS:
        if target['asg-spot-name'] not in groups or target['asg-on-demand-name'] not in groups:
            print "Pair target {} and {} are not correct".format(target['asg-spot-name'],
                                                                 target['asg-on-demand-name'])
            continue
        # First, we need to determine the number of running spot and on-demand instances
        running_spot = 0
        if 'Instances' in groups[target['asg-spot-name']]:
            running_spot = len(groups[target['asg-spot-name']]['Instances'])
        running_on_demand = 0
        if 'Instances' in groups[target['asg-on-demand-name']]:
            running_on_demand = len(groups[target['asg-on-demand-name']]['Instances'])
        # Check the number of desired spot instances
        desired_spot_count = groups[target['asg-spot-name']]['DesiredCapacity']
        # Margin
        margin_spot = min(running_spot, desired_spot_count)
        # Calculate
        needed = target['minimum-total-count'] - margin_spot - running_on_demand
        # Check number of registered instances in ECS
        registered_instances = ecs_client.multi_request("list_container_instances", {
                                                        'cluster': target['ecs-cluster-name']
                                                        })
        total_registered_instances = len(registered_instances["containerInstanceArns"])
        changed_flag = False
        # Check if reverse failover is needed (on-demand -> spot)
        if needed < 0 and running_on_demand > target['minimum-on-demand-count'] \
           and total_registered_instances >= target['minimum-total-count']:
            # If all ECS task status are OK, then proceed in decreasing on-demand instances
            services_status = retrieve_services_status(ecs_client, target['ecs-cluster-name'])
            if services_status:
                diff = max(needed, target['minimum-total-count'] - total_registered_instances)
                if diff > 0:
                    return "failed"
                elif diff == 0:
                    return "finished (waiting for new instance registration)"
                number_to_set = max(groups[target['asg-on-demand-name']]['DesiredCapacity'] + diff,
                                    target['minimum-on-demand-count'])
                autoscaling_client.raw_request("set_desired_capacity", {
                                                   'AutoScalingGroupName': target['asg-on-demand-name'],
                                                   'DesiredCapacity': number_to_set
                                               })
                changed_flag = True
        # Check if failover is needed (spot -> on-demand)
        elif needed > 0 or running_on_demand < target['minimum-on-demand-count']:
            # add additional needed instances
            number_to_set = max(running_on_demand + needed, target['minimum-on-demand-count'])
            autoscaling_client.raw_request("set_desired_capacity", {
                                               'AutoScalingGroupName': target['asg-on-demand-name'],
                                               'DesiredCapacity': number_to_set
                                          })
            changed_flag = True
        if changed_flag:
            message = "Failover Instances Script\n"
            message += "=============================================\n"
            message += "Set desired capacity of {} (on-demand group) to {}\n". \
                       format(target['asg-on-demand-name'], number_to_set)
            message += "Number of running spot instances: {}\n".format(running_spot)
            message += "Number of running on-demand instances: {}\n".format(running_on_demand)
            message += "Number of minimum on-demand instances: {}\n".format(target['minimum-on-demand-count'])
            message += "Number of minimum total instances: {}".format(target['minimum-total-count'])
            send_slack_message(message)
    return "finished"


# Retrieve list of available ASG groups
def retrieve_asg_groups(client):
    response = client.multi_request("describe_auto_scaling_groups")
    groups = {group["AutoScalingGroupName"]: group for group in response["AutoScalingGroups"]}
    return groups


# Check whether all ECS services in a specified cluster satisfy running count >= desired count
def retrieve_services_status(client, cluster_name):
    status = True
    response = client.multi_request("list_services", {"cluster": cluster_name})
    if 'serviceArns' not in response:
        print "serviceArns is not in response"
        return False
    services = []
    for service in response['serviceArns']:
        services.append(service)
    results = client.raw_request("describe_services", {"cluster": cluster_name, "services": services})
    if results['failures']:
        print "Failure in retrieving services information"
        return False
    for service in results['services']:
        if service['desiredCount'] > service['runningCount']:
            print "{} does not satisfy desiredCount <= runningCount".format(service['serviceName'])
            status = False
    return status


# Class to handle multiple pages of boto3 responses
# Adapted from https://github.com/mscansian/aws-fasi/blob/23575277b0501ae259ad5f5e5b211e187c4fa0cc/lambda.py with some changes
class BotoClientFacade(object):
    """High level boto3 requests"""
    def __init__(self, service_name, region_name):
        self._boto_client = boto3.client(service_name, region_name=region_name)

    def multi_request(self, request_name, parameters=None):
        """Emulate pagination as a single request"""
        parameters = {} if parameters is None else parameters
        if "NextToken" in parameters:
            raise Exception("'NextToken' parameter is not allowed in multi_request")

        full_response = {}
        while True:
            response = self.raw_request(request_name, parameters)
            for key, value in response.items():
                if isinstance(value, list):
                    if key not in full_response:
                        full_response[key] = []
                    full_response[key] += value
                else:
                    if key not in full_response:
                        full_response[key] = []
                    full_response[key].append(value)
            try:
                parameters["NextToken"] = response.get("NextToken", None)
                if not parameters["NextToken"]:
                    break
            except KeyError:
                break
        return full_response

    def raw_request(self, request_name, parameters=None):
        parameters = {} if parameters is None else parameters
        request = getattr(self._boto_client, request_name)
        return request(**parameters)


# Send message to slack
def send_slack_message(message):
    if SLACK_WEBHOOK_URL is None or SLACK_CHANNEL is None:
        print "no webhook or channel for Slack, Message: \n", message
        return

    slack_message = {
        'channel': SLACK_CHANNEL,
        'text': message
    }

    req = Request(SLACK_WEBHOOK_URL, json.dumps(slack_message))
    try:
        response = urlopen(req)
        response.read()
        print "Message \"{}\" is sent to slack successfully!".format(message)
    except HTTPError as e:
        print "HTTPError in sending slack message"
    except URLError as e:
        print "URLError in sending slack message"
