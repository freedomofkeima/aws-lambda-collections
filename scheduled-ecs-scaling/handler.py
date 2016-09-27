#!/usr/bin/env python
import boto3
import json
from botocore.exceptions import ClientError
from urllib2 import Request, urlopen, URLError, HTTPError

# FILL THESE REQUIRED VARIABLES
SLACK_WEBHOOK_URL = "YOUR_SLACK_WEBHOOK"  # Slack is optional (set it to None)
SLACK_CHANNEL = "YOUR_SLACK_CHANNEL"  # Slack is optional (set it to None)


def main(event, context):
    message = "List of ECS services scaling operations\n"
    message += "=============================================\n"

    for target in event:
        region = target.get('region-name')
        if not region:
            print "region-name is not correctly specified"
            return

        ecs_client = BotoClientFacade("ecs", region)
        cluster = target.get('cluster-name')
        service = target.get('service-name')

        if not cluster:
            print "cluster-name is not correctly specified"
            return

        if not service:
            print "service-name is not correctly specified"
            return

        try:
            desired_count = int(target.get('desired-count'))
        except ValueError, e:
            print "Desired count of {} must be an integer".format(service)

        # Get current details
        details = ecs_client.raw_request("describe_services", {
            "cluster": cluster,
            "services": [service]
        })

        # Set desired count
        ecs_client.raw_request("update_service", {
            "cluster": cluster,
            "service": service,
            "desiredCount": desired_count
        })

        message += "Set Desired Count of {}:{} from {} to {}\n".format(
            cluster,
            service,
            details.get('services',[{}])[0].get('desiredCount'),
            desired_count
        )

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
