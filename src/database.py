## database.py
## Kenneth Mayer and Muhammad Saber
## Implements the backend database for our simple distributed bookstore system.

from copy import copy
from typing import Any, Dict, Optional, Set, Callable

class Database:
    """
    A database is a mapping from string-valued keys to Any-valued values. We perform
    reads and writes on entire objects, rather than on attributes within
    objects.
    """
    def __init__(self) -> None:
        self.data: Dict[str, Any] = {}

    def __str__(self) -> str:
        return str(self.data)

    def write(self, name: str, val: Any) -> None:
        self.data[name] = val
        #print('dbwrite: ', name, self.data[name])

    def read(self, name: str) -> Any:
        if name in self.data:
            #print('dread:', name, self.data[name])
            val = copy(self.data[name])
            return val
        else:
            return False

class CachingDatabaseWrapper:
    """
    A CachingDatabaseWrapper provides the twrite/tread/tdelete interface.
    A CachingDatabaseWrapper wrapper acts like a database,
    but writes are buffered in a local cache, and reads read from this cache
    (or the database, if the object being read hasn't been written).
    """
    def __init__(self, db: Database) -> None:
        self.db = db
        self.copies: Dict[str, Any] = {}
        self.read_set: Set[str] = set()

    def write(self, name: str, val: Any) -> None:
        print('cwrite: ',name,val)
        self.copies[name] = val

    def read(self, name: str) -> Any:
        self.read_set.add(name)
        #print('readset: ', self.read_set)
        if name in self.copies:
            #print('cread:', name)
            return self.copies[name]
        else:
            return self.db.read(name)

    def commit(self) -> None:
        for k, v in self.copies.items():
            self.db.write(k, v)

    def get_write_set(self) -> Set[str]:
        #print (set(self.copies.keys()))
        return set(self.copies.keys())

    def get_read_set(self) -> Set[str]:
        return self.read_set

Transaction = Callable[[CachingDatabaseWrapper], None]
