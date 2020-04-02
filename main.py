import logging
import os
from resources import Resources


LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)



def main():
    resources = Resources()
    resources.load_info_instances()
    resources.load_info_volumes()
    resources.apply_tags_volumes()
    resources.show_report()
    resources.add_metrics()
    resources.aws.push_metrics()


def handler(event, context):
    main()


if __name__ == '__main__':
    main()
