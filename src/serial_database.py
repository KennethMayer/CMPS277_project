## transaction_manager.py
## Kenneth Mayer and Muhammad Saber
## Implements a serial transaction executor with optimal concurrency control for our simple distributed bookstore system.

from typing import Callable, Dict, List

from database import CachingDatabaseWrapper, Database, Optional, Transaction

class SerialTransactionExecutor:
    def __init__(self, db: 'SerialDatabase', txn: Transaction) -> None:
        self.db = db
        self.cached_db = CachingDatabaseWrapper(db)
        self.txn = txn
        self.start_tn = self.db._get_tnc()

    def read_phase(self):
        return self.txn(self.cached_db)

    def validate_and_write_phase(self) -> bool:
        finish_tn = self.db._get_tnc()
		# to implement the replication layer, we need to call it here.
		# the replica running here checks (with some byzantine algorithm)
		# whether there is any conflict with pending txns on other replicas,
		# the same way it checks for it here.
        for tn in range(self.start_tn + 1, finish_tn + 1):
            cached_db = self.db._get_transaction(tn)
            write_set = cached_db.get_write_set()
            read_set = self.cached_db.get_read_set()
            if not write_set.isdisjoint(read_set):
                return False
        self.db._commit_transaction(self.cached_db)
        #print('committed')
        return True

class SerialDatabase(Database):
    def __init__(self) -> None:
        Database.__init__(self)
        self.transactions: Dict[int, CachingDatabaseWrapper] = {}
        self.tnc: int = 0

    def _get_tnc(self) -> int:
        return self.tnc

    def _get_transaction(self, tn: int) -> CachingDatabaseWrapper:
        assert tn in self.transactions
        return self.transactions[tn]

    def _commit_transaction(self, db: CachingDatabaseWrapper) -> None:
        self.tnc += 1
        assert self.tnc not in self.transactions
        self.transactions[self.tnc] = db
        db.commit()

    def begin(self, txn: Transaction) -> SerialTransactionExecutor:
        return SerialTransactionExecutor(self, txn)
