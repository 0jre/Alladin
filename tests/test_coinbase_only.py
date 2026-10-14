import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from alladin.models import Config,SOL,USDC
from alladin.providers import collect
from alladin.finance import evidence_envelope
from alladin.models import Portfolio
from alladin.risk import security_checks
from alladin.prompts import PromptLibrary
from alladin.transport import DataError
from alladin.engine import Service
from alladin.diagnostics import diagnose


class CoinbaseOnlyTests(unittest.TestCase):
    def market(self):
        return dict(product_id='SOL-USDC',source='coinbase_advanced_sol_spot',observed_at=1000,
                    price=100,liquidity_usd=1e7,volume_24h_usd=5e7,buy_sell_imbalance=0)

    def test_collect_requires_no_network_other_than_supplied_coinbase_reader(self):
        calls=[]
        def reader():calls.append('coinbase');return self.market()
        with patch('alladin.providers.time.time',return_value=1000):s=collect(market=reader)
        self.assertEqual(calls,['coinbase'])
        self.assertFalse(s.account_checked);self.assertFalse(s.cluster_verified)
        self.assertIsNone(s.slot)
        self.assertEqual(security_checks(s,Config(),1000),[])
        e=evidence_envelope({'ready':True,'bar_closed_at':1000},s,Portfolio(250,250,250),Config(),[],1000)
        for key in ['account_checked','cluster_verified','slot','mint_authority','freeze_authority','token_program','top10_account_share']:
            self.assertNotIn(key,e['snapshot']);self.assertNotIn('snapshot.'+key,e['evidence_registry'])
        self.assertIn('onchain_data',e['data_quality']['missing_domains'])

    def test_product_identity_and_original_timestamp_are_required(self):
        for overrides in [{'product_id':'SOL-USD'},{'source':'arbitrary'},{'observed_at':900},{'observed_at':1031}]:
            with patch('alladin.providers.time.time',return_value=1000):
                with self.assertRaises(DataError):collect(market={**self.market(),**overrides})
        with self.assertRaises(DataError):collect(mint=USDC,market=self.market())

    def test_runtime_has_no_rpc_implementation_or_rpc_configuration(self):
        root=Path(__file__).resolve().parents[1]/'alladin'
        code='\n'.join(x.read_text() for x in root.glob('*.py'))
        for forbidden in ['class SolanaRPC','SOLANA_RPC_URL','api.mainnet-beta.solana.com','getGenesisHash','getAccountInfo']:
            self.assertNotIn(forbidden,code)

    def test_prompt_role_and_bundle_are_versioned_without_onchain_claims(self):
        prompts=PromptLibrary()
        self.assertEqual(prompts.metadata()['version'],'2.1.0')
        self.assertIn('quality',prompts.ROLES);self.assertNotIn('onchain',prompts.ROLES)
        self.assertIn('No blockchain RPC',prompts.render('quality'))
        with self.assertRaises(DataError):prompts.render('onchain')

    def test_legacy_task_requires_reprepare_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=Service(Config(),Path(tmp)/'session.sqlite')
            with service.store.transaction() as db:
                state=service._load(db);state['external_task']={'protocol':'external-session-v1'}
                service.store.save(db,state)
            with patch('alladin.engine.collect',side_effect=AssertionError('network')):
                with self.assertRaisesRegex(ValueError,'protocolo antigo'):
                    service.command('submit_decision',{},'legacy')
            self.assertEqual(service.status()['cash_usdc'],10000)
