import io
import json
import os
import tempfile
import unittest

from alladin.engine import Service
from alladin.mcp_server import handle, read_message, serve, write_message
from alladin.models import Config


def frame(payload):
    raw = io.BytesIO()
    write_message(raw, payload)
    raw.seek(0)
    return read_message(raw)


class MCPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = Config.load(os.path.join(os.path.dirname(__file__), '..', 'config.json'))
        self.service = Service(cfg, os.path.join(self.tmp.name, 'session.sqlite'), 'rules')

    def tearDown(self):
        self.tmp.cleanup()

    def test_initialize_lists_solana_paper_tools_only(self):
        message = frame({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}})
        opened = handle(self.service, message)
        self.assertEqual(opened['protocolVersion'], '2025-06-18')
        self.assertEqual(opened['serverInfo']['name'], 'alladin')
        listed = handle(self.service, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
        names = {tool['name'] for tool in listed['tools']}
        self.assertIn('paper_tick', names)
        self.assertNotIn('coinbase_order', names)
        self.assertNotIn('market_radar', names)
        prompts = handle(self.service, {'jsonrpc': '2.0', 'id': 4, 'method': 'prompts/list'})
        self.assertEqual({p['name'] for p in prompts['prompts']},{'alladin_market','alladin_onchain','alladin_flow','alladin_challenger','alladin_manager'})

    def test_stdio_loop_answers_and_ignores_notifications(self):
        incoming = io.BytesIO()
        write_message(incoming, {'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        write_message(incoming, {'jsonrpc': '2.0', 'id': 7, 'method': 'tools/call', 'params': {
            'name': 'alladin_status', 'arguments': {}}})
        incoming.seek(0)
        outgoing = io.BytesIO()
        code = serve(self.service, incoming, outgoing)
        self.assertEqual(code, 0)
        outgoing.seek(0)
        reply = read_message(outgoing)
        self.assertEqual(reply['id'], 7)
        status = json.loads(reply['result']['content'][0]['text'])
        self.assertEqual(status['venue'], 'coinbase_advanced')
        self.assertIsNone(read_message(outgoing))

    def test_unknown_tool_is_a_tool_error(self):
        result = handle(self.service, {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {
            'name': 'exec', 'arguments': {'cmd': 'ls'}}})
        self.assertTrue(result['isError'])


if __name__ == '__main__':
    unittest.main()
