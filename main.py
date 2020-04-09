import logging
import os
from resources import Resources


LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


def discovery_apply():
    resources = Resources()

    #resources.apply_tags_instances()
    resources.apply_tags_volumes()

    resources.show_report()
    resources.add_metrics()
    resources.aws.push_metrics()


def handler_discovery_apply(event, context):
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
    import argparse

    parser = argparse.ArgumentParser(description='AWS Resource Tagger.')

    parser.add_argument('-i', '--instance',
                    metavar="InstanceId", type=str,
                    help='Instance ID to tag. Eg: i-12345678')

    args = parser.parse_args()

    if args.instance:
        handler_event({
            "detail": {
                "instance-id": "{}".format(args.instance)
            }
        }, None)
    else:
        print("Option not found, please use -h")
