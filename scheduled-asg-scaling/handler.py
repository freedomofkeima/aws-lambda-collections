#!/usr/bin/env python
import boto3
import json
from botocore.exceptions import ClientError
from urllib2 import Request, urlopen, URLError, HTTPError

# FILL THESE REQUIRED VARIABLES
SLACK_WEBHOOK_URL = "YOUR_SLACK_WEBHOOK"  # Slack is optional (set it to None)
SLACK_CHANNEL = "YOUR_SLACK_CHANNEL"  # Slack is optional (set it to None)


def update_desired_capacity(client, detail, desired_capacity):
    asg_name = detail.get('AutoScalingGroupName')

    # Validation
    if not asg_name:
        return "Please specify correct asg-name\n"

    try:
        int(desired_capacity)
    except ValueError, e:
        return "Desired capacity of {} must be an integer\n".format(
            asg_name
        )

    # Constraint check
    if desired_capacity > detail['MaxSize']:
        return "DesiredCapacity of {} must not be greater than MaxSize\n".format(
            asg_name
        )
    if desired_capacity < detail['MinSize']:
        return "DesiredCapacity {} must not be lesser than MinSize\n".format(
            asg_name
        )

    # Set desired capacity
    try:
        client.raw_request("set_desired_capacity", {
            'AutoScalingGroupName': asg_name,
            'DesiredCapacity': desired_capacity
        })
    except ClientError, e:
        return "ClientError in calling set_desired_capacity for {}".format(
            asg_name
        )

    return "Set DesiredCapacity of {} from {} to {}\n".format(
        asg_name,
        detail['DesiredCapacity'],
        desired_capacity
    )


def process_max_type(client, asgs, details, desired_capacity):
    resp = ""
    chosen_asg_detail = {}
    max_desired = 0

    for asg in asgs:
        detail = details[asg]
        if detail['DesiredCapacity'] > max_desired:
            chosen_asg_detail = detail
            max_desired = detail['DesiredCapacity']

    resp += update_desired_capacity(
        client,
        chosen_asg_detail,
        desired_capacity
    )

    return resp


def process_all_type(client, asgs, details, desired_capacity):
    resp = ""

    for asg in asgs:
        detail = details[asg]
        resp += update_desired_capacity(client, detail, desired_capacity)

    return resp


def main(event, context):
    message = "List of scheduled ASG desired capacity scaling operations\n"
    message += "=============================================\n"

    for target in event:
        region = target.get('region-name')
        if not region:
            print "region-name is not correctly specified"
            return

        asg_client = BotoClientFacade("autoscaling", region)
        asgs = target.get('asg-name', [])

        # Append message
        message += ', '.join(asgs)
        message += ":\n"

        # Retrieve ASG information
        response = asg_client.multi_request("describe_auto_scaling_groups", {
            'AutoScalingGroupNames': asgs
        })
        details = {}

        # Parse KV with Key = 'AutoScalingGroupName'
        for entity in response['AutoScalingGroups']:
            details[entity['AutoScalingGroupName']] = entity

        # Check for type
        if target.get('type', '') == "max":
            message += process_max_type(
                asg_client,
                asgs,
                details,
                target.get('desired-capacity')
            )
        elif target.get('type', '') == "all":
            message += process_all_type(
                asg_client,
                asgs,
                details,
                target.get('desired-capacity')
            )
        else:
            message += "type is not recognized\n"
            print "type is not correctly specified"
            continue
        # Add newline
        message += "\n"

    send_slack_message(message)
    return "finished"

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
