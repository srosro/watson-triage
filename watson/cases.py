"""Durable per-issue workflow state, separate from immutable analysis runs."""
import json
from .core import now


class Cases:
    def __init__(self, store):
        self.store = store
        store.db.executescript('''
        CREATE TABLE IF NOT EXISTS cases (
          repo TEXT, number INTEGER, cursor TEXT, state TEXT, data TEXT, updated TEXT,
          PRIMARY KEY(repo,number));
        CREATE TABLE IF NOT EXISTS validations (
          id INTEGER PRIMARY KEY, repo TEXT, number INTEGER, sha TEXT, result TEXT, created TEXT);
        ''')

    def get(self, repo, number):
        row = self.store.db.execute('SELECT * FROM cases WHERE repo=? AND number=?', (repo,number)).fetchone()
        return dict(row, data=json.loads(row['data'])) if row else None

    def save(self, repo, number, cursor, state, data):
        """Commit the cursor, and anything staged beside it, as ONE transaction.

        The cursor is a point of no return: once it advances, the next cycle
        reads the issue as unchanged. A pending action staged before this call
        therefore has to land with it or not at all -- committed separately, a
        failure between the two leaves a claim with no cursor (the retry
        collides with its own key and the issue is stuck for good) or a cursor
        with no claim (the update is silently dropped). One commit has neither
        half-state, and it is why `stage_action` exists beside `claim_action`.
        """
        try:
            self.store.db.execute('''INSERT INTO cases VALUES(?,?,?,?,?,?) ON CONFLICT(repo,number)
              DO UPDATE SET cursor=excluded.cursor,state=excluded.state,data=excluded.data,updated=excluded.updated''',
              (repo,number,cursor,state,json.dumps(data,ensure_ascii=False),now()))
            self.store.db.commit()
        except Exception:
            # Abort whatever was staged beside this. SQLite does NOT auto-abort
            # the transaction for most statement errors, and the caller catches
            # per issue and keeps using this connection -- so an orphaned claim
            # would ride the NEXT issue's commit and land without its cursor,
            # which is the stuck-forever half-state this method exists to
            # prevent. Rolling back here is what makes the guarantee hold on
            # the failure path, not just the happy one.
            self.store.db.rollback()
            raise

    def validation(self, repo, number, sha, result):
        self.store.db.execute('INSERT INTO validations(repo,number,sha,result,created) VALUES(?,?,?,?,?)',
                             (repo,number,sha,json.dumps(result,ensure_ascii=False),now()))
        self.store.db.commit()

    def history(self, repo, number):
        return [json.loads(x['result']) for x in self.store.db.execute(
            'SELECT result FROM validations WHERE repo=? AND number=? ORDER BY id DESC LIMIT 5', (repo,number))]
