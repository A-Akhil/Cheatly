import sqlite3

# Test 1: FTS5 basic
try:
    c = sqlite3.connect(':memory:')
    c.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
    print("FTS5 basic: OK")
except Exception as e:
    print(f"FTS5 basic: FAIL - {e}")

# Test 2: FTS5 porter tokenizer
try:
    c2 = sqlite3.connect(':memory:')
    c2.execute("CREATE VIRTUAL TABLE t USING fts5(x, tokenize='porter unicode61')")
    print("FTS5 porter: OK")
except Exception as e:
    print(f"FTS5 porter: FAIL - {e}")

# Test 3: Check existing rag_store.db tables
try:
    import os
    db_path = os.path.join("backend", "context", "rag_store.db")
    c3 = sqlite3.connect(db_path)
    tables = c3.execute("SELECT name FROM sqlite_master WHERE type IN ('table','shadow') OR type='table'").fetchall()
    print(f"rag_store.db tables: {[t[0] for t in tables]}")
    c3.close()
except Exception as e:
    print(f"rag_store.db check: FAIL - {e}")
