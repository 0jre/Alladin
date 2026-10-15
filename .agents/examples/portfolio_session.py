"""Read/rank through the backend; external sessions own all reasoning.

Set LAB_API_TOKEN and run against the portfolio HTTP service and worker.
This example never submits a trade automatically.
"""
import json
from alladin.client import BackendClient


def main():
    client=BackendClient()
    brief=client.command('get_session_brief',{},'example-read-brief')
    if brief.get('execution')!='paper' or brief.get('backend')!='portfolio':
        raise ValueError('Expected a portfolio paper backend')
    reconciliation=client.command('reconcile',{},'example-read-reconcile')
    if not reconciliation['valid']:
        raise ValueError('Internal reconciliation failed; entries remain blocked')
    scan=client.command('scan_opportunities',{'limit':5},'example-read-scan')
    print(json.dumps({'brief':brief,'scan':scan},indent=2))


if __name__=='__main__':
    main()
