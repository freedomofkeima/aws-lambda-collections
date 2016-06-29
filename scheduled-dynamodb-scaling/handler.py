#!/usr/bin/env python
import boto3
import json
from botocore.exceptions import ClientError
from urllib2 import Request, urlopen, URLError, HTTPError

# FILL THESE REQUIRED VARIABLES
SLACK_WEBHOOK_URL = "YOUR_SLACK_WEBHOOK"  # Slack is optional (set it to None)
SLACK_CHANNEL = "YOUR_SLACK_CHANNEL"  # Slack is optional (set it to None)


def main(event, context):
    message = "List of scheduled DynamoDB throughput operations\n"
    message += "=============================================\n"
    for target in event:
        region = target.get('region-name')
        if not region:
            print "region-name is not correctly specified"
            return
        dynamodb_client = BotoClientFacade("dynamodb", region)
        try:
            response = dynamodb_client.raw_request("describe_table", {
                'TableName': target.get('table-name', '')
            })
            provisioned = response['Table']['ProvisionedThroughput']
            # Check limit of number decreases
            if provisioned['NumberOfDecreasesToday'] > 3:
                print "Daily decrement limit reached"
                continue
            # Modify throughput
            if provisioned['ReadCapacityUnits'] != target['read-throughput'] \
                    or provisioned['WriteCapacityUnits'] != target['write-throughput']:
                # Update table throughput provisioning
                dynamodb_client.raw_request("update_table", {
                    'TableName': target['table-name'],
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': target['read-throughput'],
                        'WriteCapacityUnits': target['write-throughput']
                    }
                })
                message += "Throughput for {} (R: {} -> {}, W: {} -> {})\n".format(
                    target['table-name'],
                    provisioned['ReadCapacityUnits'],
                    target['read-throughput'],
                    provisioned['WriteCapacityUnits'],
                    target['write-throughput']
                )
            else:
                message += "Throughput for {} is not changed (R/W: {}/{})\n".format(
                    target['table-name'],
                    provisioned['ReadCapacityUnits'],
                    provisioned['WriteCapacityUnits']
                )
        except ClientError, e:
            print "Ensure table-name is correctly specified"
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
