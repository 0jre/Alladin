import tempfile
import unittest
from pathlib import Path
from alladin.storage import Store


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'audit.sqlite')
        with self.store.transaction() as db:
            self.store.event(db, 1, 'decision', {'action': 'HOLD'})
            self.store.event(db, 2, 'decision', {'action': 'BUY'})

    def test_restart_and_anchor(self):
        report = self.store.verify_audit()
        self.assertTrue(report['valid'])
        self.assertEqual(report['count'], 2)
        self.assertTrue(Store(self.store.path).verify_audit(report['head'])['valid'])
        self.assertFalse(self.store.verify_audit('0' * 64)['valid'])

    def test_tampering(self):
        with self.store.transaction() as db:
            db.execute("UPDATE events SET payload='{}' WHERE seq=1")
        self.assertFalse(self.store.verify_audit()['valid'])

    def test_tail_deletion_detected_with_anchor(self):
        head = self.store.verify_audit()['head']
        with self.store.transaction() as db:
            db.execute('DELETE FROM events WHERE seq=2')
            db.execute('DELETE FROM event_seals WHERE seq=2')
        self.assertFalse(self.store.verify_audit(head)['valid'])

    def test_rollback(self):
        head = self.store.verify_audit()['head']
        with self.assertRaises(RuntimeError):
            with self.store.transaction() as db:
                self.store.event(db, 3, 'decision', {})
                raise RuntimeError('abort')
        self.assertTrue(self.store.verify_audit(head)['valid'])
