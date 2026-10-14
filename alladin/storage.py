import hashlib
import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# WAL + synchronous=NORMAL keeps commits atomic and process-crash consistent
# without paying an fsync per command. Only an OS crash or power loss can drop
# a just-committed transaction; the idempotent command model tolerates that —
# a lost command loses its idempotency record too, so a retry with the same
# key re-executes cleanly instead of replaying a phantom result.
_SYNC = 'NORMAL'
# Bound WAL growth without a checkpoint on every command close.
_CHECKPOINT_EVERY = 128

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)

class Store:
    def __init__(self,path):
        self.path = str(path)
        self._writes = 0
        Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS event_seals (seq INTEGER PRIMARY KEY, previous TEXT NOT NULL, digest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS requests (key TEXT PRIMARY KEY, digest TEXT NOT NULL, response TEXT NOT NULL);
            ''')
    def _open(self):
        db = sqlite3.connect(self.path,timeout=60)
        db.execute('PRAGMA busy_timeout=60000')
        db.execute(f'PRAGMA synchronous={_SYNC}')
        # The automatic checkpoint on last-connection close dominated command
        # latency. When the driver supports disabling it, the periodic PASSIVE
        # checkpoint in transaction() bounds the WAL instead.
        if hasattr(db,'setconfig') and hasattr(sqlite3,'SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE'):
            db.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE,True)
        return db
    @contextmanager
    def connect(self):
        db = self._open()
        try:
            yield db
        finally:
            db.close()
    @contextmanager
    def transaction(self):
        db = self._open()
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
            self._writes += 1
            if self._writes % _CHECKPOINT_EVERY == 0:
                try:
                    db.execute('PRAGMA wal_checkpoint(PASSIVE)')
                except Exception:
                    pass  # checkpoint nunca altera o resultado do comando já confirmado
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
    def load(self,db):
        row = db.execute('SELECT payload FROM state WHERE id=1').fetchone()
        return json.loads(row[0]) if row else None
    def save(self,db,state):
        db.execute('INSERT INTO state VALUES (1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(canonical(state),))
    def event(self,db,ts,kind,payload):
        row = db.execute('SELECT digest FROM event_seals ORDER BY seq DESC LIMIT 1').fetchone()
        previous = row[0] if row else '0' * 64
        cursor = db.execute('INSERT INTO events(ts,kind,payload) VALUES (?,?,?)',(ts,kind,canonical(payload)))
        seq = cursor.lastrowid
        digest = hashlib.sha256(canonical([previous,seq,ts,kind,payload]).encode()).hexdigest()
        db.execute('INSERT INTO event_seals VALUES (?,?,?)',(seq,previous,digest))
    def verify_audit(self, expected_head=None):
        """Detect modification/deletion against an optionally externally anchored head.

        Hashes are not signatures. A DB administrator can rewrite the whole chain;
        externally retaining the returned head is required to detect that case.
        Legacy databases without seals fail validation rather than being re-sealed.
        """
        previous = '0' * 64
        count = 0
        with self.connect() as db:
            rows = db.execute('SELECT e.seq,e.ts,e.kind,e.payload,s.previous,s.digest FROM events e LEFT JOIN event_seals s ON e.seq=s.seq ORDER BY e.seq')
            for seq,ts,kind,payload,parent,digest in rows:
                count += 1
                actual = hashlib.sha256(canonical([previous,seq,ts,kind,json.loads(payload)]).encode()).hexdigest()
                if seq != count or parent != previous or digest != actual:
                    return dict(valid=False, first_invalid_seq=seq, count=count)
                previous = digest
            seals = db.execute('SELECT COUNT(*) FROM event_seals').fetchone()[0]
        valid = seals == count and (expected_head is None or expected_head == previous)
        return dict(valid=valid, count=count, head=previous)

    def audit(self,limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('limit deve estar entre 1 e 1000')
        with self.connect() as db:
            rows = db.execute('SELECT seq,ts,kind,payload FROM events ORDER BY seq DESC LIMIT ?',(limit,)).fetchall()
        return [dict(seq=a,timestamp=b,kind=c,payload=json.loads(d)) for a,b,c,d in reversed(rows)]
    def lookup(self,db,key,request):
        if not isinstance(key,str) or not 1 <= len(key) <= 128:
            raise ValueError('Idempotency-Key obrigatória: 1–128 caracteres')
        digest = hashlib.sha256(canonical(request).encode()).hexdigest()
        old = db.execute('SELECT digest,response FROM requests WHERE key=?',(key,)).fetchone()
        if old:
            if old[0] != digest:
                raise ValueError('Idempotency-Key reutilizada com conteúdo diferente')
            return json.loads(old[1])
        return None
    def once(self,db,key,request,callback):
        old = self.lookup(db,key,request)
        if old is not None:
            return old
        digest = hashlib.sha256(canonical(request).encode()).hexdigest()
        response = callback()
        db.execute('INSERT INTO requests VALUES (?,?,?)',(key,digest,canonical(response)))
        return json.loads(canonical(response))
