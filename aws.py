
import os
import json
import boto3


defaults = {
    "query_instances": """
        SELECT
            resourceId,
            configuration.imageId,
            configuration.blockDeviceMappings,
            tags,
            relationships
        WHERE
            resourceType = 'AWS::EC2::Instance'
            AND configuration.state.name = 'running'
            OR configuration.state.name = 'stopped'
    """
}


class AWS(object):
    def __init__(self):
        self.clients = {}
        self.config_queries = {}

        self.metric_namespace = "aws_resource_tagger"
        self.metrics_data = []

        self.setup()
    
    def setup(self):
        self.metrics_data.clear()

        self.clients["ec2"] = config = boto3.client('ec2')
        self.clients["config"] = config = boto3.client('config')
        self.clients["cloudwatch"] = config = boto3.client('cloudwatch')

        self.config_queries["instances"] = os.getenv("CONFIG_QUERY_INSTANCES", defaults["query_instances"])

    def get_instances(self):
        instances = []
        instances.clear()

        page = ''
        next_page = True
        while next_page:
            if page == '':
                response = self.clients["config"].select_resource_config(Expression=self.config_queries["instances"])
            else:
                response = self.clients["config"].select_resource_config(Expression=self.config_queries["instances"], NextToken=page)
            
            if 'NextToken' in response:
                page = response["NextToken"]
            else:
                next_page = False

            for r in response['Results']:
                instances.append(json.loads(r))

        return instances

    def get_volumes(self):
        volumes = {}
        volumes.clear()
        for response in self.clients["ec2"].get_paginator('describe_volumes').paginate():
            volumes.update([(volume['VolumeId'], volume) for volume in response['Volumes']])
        
        return volumes

    def add_metrics(self, data={}):
        self.metrics_data.append({
            "MetricName": data["name"],
            "Dimensions": [data["dimensions"]],
            "Value": data["value"],
            "Unit": "Count"
        })

    def push_metrics(self):
        self.clients["cloudwatch"].put_metric_data(
            Namespace=self.metric_namespace,
            MetricData=self.metrics_data
        )
        self.metrics_data.clear()
