
import os
import json
import boto3


defaults = {
    "query_instances": """
        SELECT
            resourceId,
            configuration.imageId,
            configuration.blockDeviceMappings,
            configuration.vpcId,
            tags,
            relationships
        WHERE
            resourceType = 'AWS::EC2::Instance'
            AND configuration.state.name = 'running'
            OR configuration.state.name = 'stopped'
    """,
    "query_vpcs": """
        SELECT
            resourceId,
            tags
        WHERE
            resourceType = 'AWS::EC2::VPC'
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

    def run_Config_query(self, query):
        response = []
        response.clear()
        page = ''
        next_page = True
        while next_page:
            if page == '':
                resp = self.clients["config"].select_resource_config(Expression=query)
            else:
                resp = self.clients["config"].select_resource_config(Expression=query, NextToken=page)

            if 'NextToken' in resp:
                page = resp["NextToken"]
            else:
                next_page = False

            for r in resp['Results']:
                response.append(json.loads(r))

        return response

    def get_instances(self):
        return self.run_Config_query(
            self.config_queries["instances"]
        )

    def get_instance_tags_Config(self, instance_id):
        """
        AWS Config has delay to ingest resources, then events
        of new resources is not instantly available on the Config.
        Therefore, to retrieve NEW resources, is not a good idea to
        use AWS Config.
         """
        query = """
            SELECT
                resourceId,
                tags,
                relationships
            WHERE
                resourceType = 'AWS::EC2::Instance'
                and resourceId = '{}'
        """.format(instance_id)
        return self.run_Config_query(query)

    def get_instance_tags_api(self, instance_id):
        """
        Get instances directly from EC2:Instance API.
        Understanding that instance_id is unique for whole
        AWS resources, only the dictionary will be returned.
        """
        instance_resp = {}
        instance_resp.clear()
        try:
            resp = self.clients["ec2"].describe_instances(
                InstanceIds=[instance_id]
            )
            if 'Reservations' not in resp:
                return instance_resp

            if len(resp["Reservations"][0]['Instances']) <= 0:
                return instance_resp

            instance = resp["Reservations"][0]['Instances'][0]
            if 'Tags' not in instance:
                tags = []
            else:
                tags = instance["Tags"]

            dm = instance["BlockDeviceMappings"] or []
            try:
                vpc_id = instance["VpcId"] or ''
            except KeyError:
                vpc_id = ''
                pass

            instance_resp = {
                "InstanceId": instance["InstanceId"],
                "Tags": tags,
                "BlockDeviceMappings": dm,
                "VpcId": vpc_id
            }
        except Exception as e:
            raise

        return instance_resp

    def get_vpc_tags(self, vpc_id):
        query = """
            SELECT
                resourceId,
                tags
            WHERE
                resourceType = 'AWS::EC2::VPC'
                AND resourceId = '{}'
        """.format(vpc_id)
        return self.run_Config_query(query)

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
