import argparse
import sys
import colorama

from src.metrics import Metrics
from src.subscription_manager import SubscriptionManager
from src.processor import Processor

VERSION = "0.0.1"


def init_args():
    """Parse and return the arguments."""

    parser = argparse.ArgumentParser(description="Simple Gmail Analyzer")
    parser.add_argument("--top", type=int, default=10, help="Number of results to show")
    parser.add_argument(
        "--user", type=str, default="me", help="User ID to fetch data for"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Verbose output, helpful for debugging"
    )
    parser.add_argument(
        "--version", action="store_true", help="Display version and exit"
    )
    parser.add_argument('command', choices=['analyze', 'subscriptions'], 
                       help='Команда для выполнения')

    args = vars(parser.parse_args())

    return args


def main():
    colorama.init()

    args = init_args()

    if args["version"]:
        print("gmail analyzer v{}".format(VERSION))
        sys.exit()

    if args['command'] == 'analyze':
        Metrics(args).start()
    elif args['command'] == 'subscriptions':
        processor = Processor()
        messages = processor.get_messages()
        processor.get_metadata(messages)
        SubscriptionManager(processor).run()


if __name__ == "__main__":
    main()
