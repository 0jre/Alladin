"""Explicit HTTP operations only; reasoning and retries belong to the caller."""
import argparse
import json
import sys
from pathlib import Path

# Permit this repository example to run without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from alladin.client import BackendClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8080')
    commands = parser.add_subparsers(dest='operation', required=True)
    commands.add_parser('status')
    prepare = commands.add_parser('prepare')
    prepare.add_argument('--key', required=True)
    submit = commands.add_parser('submit')
    submit.add_argument('--file', required=True)
    submit.add_argument('--key', required=True)
    args = parser.parse_args()
    client = BackendClient(args.url)
    if args.operation == 'status':
        result = client.status()
    elif args.operation == 'prepare':
        result = client.command('prepare_decision', {}, args.key)
    else:
        payload = json.loads(Path(args.file).read_text())
        result = client.command('submit_decision', payload, args.key)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
