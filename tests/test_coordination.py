"""Concurrent external decisions against independently advancing paper workers."""
import json
import threading
import unittest
from unittest.mock import patch

import test_pipeline as fixture
from alladin.engine import Service
from alladin.external import context_hash
from alladin.transport import DataError


class CoordinationTests(unittest.TestCase):
    def setUp(self):
        fixture.PipelineTests.setUp(self)
        self.clock.stop()
        self.clock=patch('alladin.engine.time.time',side_effect=lambda:self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
    source_json = fixture.PipelineTests.source_json
    submission = fixture.PipelineTests.submission

    def prepare(self):
        self.service.command('paper_tick', {}, 'warm')
        return self.service.command('prepare_decision', {}, 'prepare')['task']

    def peer(self):
        return Service(self.cfg, self.service.store.path)

    def test_preparation_coalesces_without_network_or_replacing_evidence(self):
        task = self.prepare()
        self.assertNotIn('analysis_snapshot',task)
        self.now += 60
        self.peer().command('paper_tick', {}, 'worker-new-bar')
        with patch('alladin.transport.HTTP.json', side_effect=AssertionError('No redundant I/O')):
            result = self.peer().command('prepare_decision', {}, 'other-preparer')
        self.assertTrue(result['reused'])
        self.assertEqual(task, result['task'])

    def test_closed_bar_changes_do_not_relabel_or_invalidate_analysis(self):
        task = self.prepare()
        original_hash = task['evidence_sha256']
        self.now += 60
        self.peer().command('paper_tick', {}, 'worker-new-bar')
        result = self.service.command('submit_decision', self.submission(task, 'LONG'), 'open')
        self.assertEqual(result['outcome'], 'opened', result)
        audit = result['decision']['council']
        self.assertEqual(audit['evidence_sha256'], original_hash)
        self.assertEqual(audit['analysis_as_of'], task['evidence']['as_of'])
        self.assertGreater(audit['risk_bar_closed_at'], task['evidence']['features']['bar_closed_at'])
        self.assertEqual(audit['execution_snapshot']['timestamp'], self.now)

    def test_worker_can_commit_a_new_bar_during_submission_io(self):
        from alladin.providers import collect as real_collect
        task = self.prepare()
        args = self.submission(task, 'LONG')
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        results, errors = [], []

        def collect(*args, **kwargs):
            if threading.current_thread().name == 'external-submit':
                entered.set()
                if not release.wait(3):
                    raise AssertionError('Worker never released submission')
            return real_collect(*args, **kwargs)

        def submit():
            try:
                results.append(self.service.command('submit_decision', args, 'open'))
            except BaseException as exc:
                errors.append(exc)

        with patch('alladin.engine.collect', side_effect=collect):
            thread = threading.Thread(target=submit, name='external-submit')
            thread.start()
            try:
                self.assertTrue(entered.wait(3))
                self.now += 60
                tick = self.peer().command('paper_tick', {}, 'concurrent-worker')
                self.assertEqual(tick['result'], 'processed')
            finally:
                release.set()
                thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(results[0]['outcome'], 'opened', results)
        self.assertEqual(self.peer().command('submit_decision', args, 'open'), results[0])
        self.assertEqual(len(self.service.status()['positions']), 1)
        self.assertTrue(self.service.store.verify_audit()['valid'])

    def test_concurrent_preparers_receive_the_same_task(self):
        from alladin.providers import collect as real_collect
        self.service.command('paper_tick', {}, 'warm')
        barrier = threading.Barrier(2)
        results, errors = [], []

        def collect(*args, **kwargs):
            barrier.wait(3)
            return real_collect(*args, **kwargs)

        def prepare(index):
            try:
                results.append(self.peer().command('prepare_decision', {}, 'prepare-' + str(index)))
            except BaseException as exc:
                errors.append(exc)

        with patch('alladin.engine.collect', side_effect=collect):
            threads = [threading.Thread(target=prepare, args=(i,)) for i in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(4)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['task'], results[1]['task'])

    def test_hold_commits_without_market_io_after_a_new_bar(self):
        task = self.prepare()
        args = self.submission(task, 'LONG')
        args['decision']['action'] = 'HOLD'
        for report in args['reports'].values():
            report['stance'] = 'HOLD'
        self.now += 60
        self.peer().command('paper_tick', {}, 'worker')
        before = self.service.status()
        with patch('alladin.transport.HTTP.json', side_effect=AssertionError('HOLD does not execute')):
            result = self.peer().command('submit_decision', args, 'hold')
        self.assertEqual(result['outcome'], 'abstained', result)
        self.assertIsNone(result['decision']['council']['execution_snapshot'])
        self.assertEqual(result['events'], [])
        self.assertEqual(self.service.status()['cash_usdc'], before['cash_usdc'])
        self.assertEqual(self.service.status()['positions'], [])

    def test_close_uses_only_current_book_and_is_not_blocked_by_entry_gap(self):
        first = self.prepare()
        self.service.command('submit_decision', self.submission(first, 'LONG'), 'open')
        second = self.service.command('prepare_decision', {}, 'next')['task']
        self.price *= 1.012  # larger than entry drift guard, below the fixture take
        real_source = self.source_json

        def book_only(url, *args, **kwargs):
            self.assertIn('/product_book', url)
            return real_source(url, *args, **kwargs)

        with patch('alladin.transport.HTTP.json', side_effect=book_only):
            result = self.service.command('submit_decision', self.submission(second, 'CLOSE'), 'close')
        self.assertEqual(result['outcome'], 'closed', result)
        self.assertEqual(self.service.status()['positions'], [])
        self.assertEqual(self.service.status()['closed_trades'], 1)

    def test_latest_shock_vetoes_entry_from_an_older_valid_thesis(self):
        from alladin.features import features
        task = self.prepare()

        def shock(rows):
            return dict(features(rows), regime='shock')

        with patch('alladin.engine.features', side_effect=shock):
            result = self.service.command('submit_decision', self.submission(task, 'LONG'), 'open')
        self.assertEqual(result['outcome'], 'risk_rejected', result)
        self.assertIn('warmup_or_shock', result['decision']['approval']['reasons'])
        self.assertEqual(result['events'], [])
        self.assertEqual(self.service.status()['cash_usdc'], 250)

    def test_transient_submit_failure_retries_the_same_key_once(self):
        task = self.prepare()
        args = self.submission(task, 'LONG')
        with patch('alladin.engine.collect', side_effect=DataError('Transient fixture failure')):
            with self.assertRaises(DataError):
                self.service.command('submit_decision', args, 'open')
        self.assertEqual(self.service.status()['external_task']['status'], 'prepared')
        result = self.peer().command('submit_decision', args, 'open')
        self.assertEqual(result['outcome'], 'opened', result)
        self.assertEqual(self.service.command('submit_decision', args, 'open'), result)
        self.assertEqual(len(self.service.status()['positions']), 1)

    def test_material_account_change_during_io_rejects_old_authority(self):
        from alladin.providers import collect as real_collect
        task = self.prepare()

        def change_account(*args, **kwargs):
            with self.service.store.transaction() as db:
                state = self.service._load(db)
                state['portfolio']['cash'] -= 1
                self.service.store.save(db, state)
            return real_collect(*args, **kwargs)

        with patch('alladin.engine.collect', side_effect=change_account):
            with self.assertRaisesRegex(ValueError, 'Contexto mudou'):
                self.service.command('submit_decision', self.submission(task, 'LONG'), 'open')
        self.assertEqual(self.service.status()['positions'], [])

    def test_submission_synchronizes_flat_history_before_entry(self):
        task = self.prepare()
        self.now += 60
        result = self.peer().command('submit_decision', self.submission(task, 'LONG'), 'open')
        self.assertEqual(result['outcome'], 'opened', result)
        tick = self.peer().command('paper_tick', {}, 'worker-after-open')
        self.assertEqual(tick['result'], 'waiting_for_closed_bar', tick)
        self.assertFalse(self.service.status()['halted'])
        self.assertEqual(len(self.service.status()['positions']), 1)

    def test_market_observations_do_not_change_account_binding(self):
        self.prepare()
        with self.service.store.connect() as db:
            state = self.service._load(db)
        before = context_hash(state)
        state['portfolio'].update(peak=251, day='new-day', day_start_equity=251)
        state['last_price'] = 102
        state['last_decision'] = {'action': 'HOLD'}
        state['curve'].append({'price': 102})
        self.assertEqual(context_hash(state), before)
        state['portfolio']['cash'] -= 1
        self.assertNotEqual(context_hash(state), before)

    def test_concurrent_submitters_cannot_duplicate_an_entry(self):
        from alladin.providers import collect as real_collect
        task = self.prepare()
        args = self.submission(task, 'LONG')
        barrier = threading.Barrier(2)
        results, errors = [], []

        def collect(*args, **kwargs):
            barrier.wait(3)
            return real_collect(*args, **kwargs)

        def submit(index):
            try:
                results.append(self.peer().command('submit_decision', args, 'open-' + str(index)))
            except ValueError as exc:
                errors.append(exc)

        with patch('alladin.engine.collect', side_effect=collect):
            threads = [threading.Thread(target=submit, args=(i,)) for i in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(4)
        self.assertEqual(len(results), 1, results)
        self.assertEqual(len(errors), 1, errors)
        self.assertEqual(results[0]['outcome'], 'opened')
        self.assertEqual(len(self.service.status()['positions']), 1)
        self.assertTrue(self.service.store.verify_audit()['valid'])

    def test_expired_task_is_rejected_before_network_and_replaced(self):
        task = self.prepare()
        self.now = task['expires_at'] + 1
        with patch('alladin.transport.HTTP.json', side_effect=AssertionError('Expired authority')):
            with self.assertRaisesRegex(ValueError, 'expirada'):
                self.service.command('submit_decision', self.submission(task, 'LONG'), 'expired')
        self.service.command('paper_tick', {}, 'resync')
        new = self.service.command('prepare_decision', {}, 'new')['task']
        self.assertNotEqual(new['id'], task['id'])
        self.assertEqual(self.service.status()['cash_usdc'], 250)

    def test_realized_stop_invalidates_old_close_authority(self):
        task = self.prepare()
        self.service.command('submit_decision', self.submission(task, 'LONG'), 'open')
        close_task = self.service.command('prepare_decision', {}, 'close-task')['task']
        self.price *= .98
        tick = self.peer().command('paper_tick', {}, 'stop')
        self.assertEqual(tick['events'][0]['event'], 'CLOSE')
        with patch('alladin.transport.HTTP.json', side_effect=AssertionError('No stale close I/O')):
            with self.assertRaises(ValueError):
                self.service.command('submit_decision', self.submission(close_task, 'CLOSE'), 'old-close')
        self.assertEqual(self.service.status()['positions'], [])
        self.assertEqual(self.service.status()['closed_trades'], 1)

    def test_current_peak_drawdown_is_rechecked_even_with_unchanged_account_binding(self):
        task = self.prepare()
        with self.service.store.transaction() as db:
            state = self.service._load(db)
            state['portfolio']['peak'] = 1000
            self.service.store.save(db, state)
        result = self.service.command('submit_decision', self.submission(task, 'LONG'), 'open')
        self.assertEqual(result['outcome'], 'risk_rejected', result)
        self.assertEqual(result['events'], [])
        self.assertTrue(self.service.status()['halted'])
        self.assertEqual(self.service.status()['positions'], [])

    def test_external_execution_validation_is_excluded_from_strategy_statistics(self):
        first = self.prepare()
        args = self.submission(first, 'LONG')
        args['decision']['strategy'] = 'execution_validation'
        opened = self.service.command('submit_decision', args, 'open')
        self.assertTrue(opened['events'][0]['validation_only'])
        second = self.service.command('prepare_decision', {}, 'close-task')['task']
        closed = self.service.command('submit_decision', self.submission(second, 'CLOSE'), 'close')
        self.assertEqual(closed['outcome'], 'closed')
        performance = self.service.performance()
        self.assertEqual(performance['execution_validation_roundtrips'], 1)
        self.assertEqual(performance['closed_roundtrips'], 0)

    def test_malformed_submission_is_rejected_before_io(self):
        task = self.prepare()
        args = self.submission(task, 'LONG')
        for value in ('LONG', [], None):
            malformed = dict(args, decision=value)
            with patch('alladin.transport.HTTP.json', side_effect=AssertionError('Malformed request')):
                with self.assertRaisesRegex(ValueError, 'Contrato'):
                    self.service.command('submit_decision', malformed, 'bad-' + str(value))
        self.assertEqual(self.service.status()['external_task']['status'], 'prepared')
        self.assertEqual(self.service.status()['positions'], [])
