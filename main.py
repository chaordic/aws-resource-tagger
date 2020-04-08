import logging
import os
from resources import Resources


LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


SAMPLE_EVENTS = {
    "instnace": {
            "version": "0",
            "id": "e024e47e-838b-62c5-9276-92213d8b064e",
            "detail-type": "EC2 Instance State-change Notification",
            "source": "aws.ec2",
            "account": "510796467886",
            "time": "2020-04-07T00:58:50Z",
            "region": "us-east-1",
            "resources": [
                "arn:aws:ec2:us-east-1:510796467886:instance/i-032f19176819dad87"
            ],
            "detail": {
                "instance-id": "i-0945d1f128bd001c1",
                "state": "running"
            }
        }
}


def main():
    resources = Resources()

    #resources.apply_tags_instances()
    resources.apply_tags_volumes()

    resources.show_report()
    resources.add_metrics()
    resources.aws.push_metrics()


def handler_discovery(event, context):
    main()


def handler_event(event, context):
    """Handle CloudWatch Event rule."""
    resources = Resources()
    try:
        resources.apply_tags_from_event(event)
    except Exception as e:
        print(e)
        raise


if __name__ == '__main__':
    #main()
    handler_event(SAMPLE_EVENTS["instnace"], None)
