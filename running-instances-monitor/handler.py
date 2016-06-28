#!/usr/bin/env python
import boto3
import json
from urllib2 import Request, urlopen, URLError, HTTPError

REGION_NAMES = [
        'ap-northeast-1',
        'ap-northeast-2',
        'ap-southeast-1',
        'ap-southeast-2',
        'us-east-1',
        'us-west-1',
        'us-west-2',
        'eu-west-1',
        'eu-central-1',
        'sa-east-1',
        'ap-south-1'
    ]

# FILL THESE REQUIRED VARIABLES
SLACK_WEBHOOK_URL = "YOUR_SLACK_WEBHOOK"
SLACK_CHANNEL = "YOUR_SLACK_CHANNEL"

def main(event, context):
    message = "List of running instances\n"
    for region in REGION_NAMES:
        temp = "=============================================\n"
        temp += "Running at {}\n".format(region)
        temp += "=============================================\n"
        ec2_client = BotoClientFacade("ec2", region)
        response = ec2_client.multi_request("describe_instances", {'Filters': [
            {
                'Name': "instance-state-name",
                'Values': ["running"]
            }
        ]})
        count = 0
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance.get('InstanceId', '')
                instance_type = instance.get('InstanceType', '')
                tags = instance.get('Tags', {})
                for tag in tags:
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                temp += "{},{} ({})\n".format(instance_id, name, instance_type)
                count = count + 1  # increment
        if count > 0:
            message += temp  # concatenate message
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
        print "no webhook or channel for Slack"
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