"""Measure OFFSET vs keyset pagination on a local SQLite messages table.

Run: python3 bench.py
Numbers are "measured here" (Python 3.14.9 sqlite3, one local file, WAL).
"""
import os
import sqlite3
import statistics
import time

DB = "bench.db"
if os.path.exists(DB):
    os.remove(DB)

con = sqlite3.connect(DB)
con.execute("PRAGMA journal_mode=WAL")
con.execute("PRAGMA synchronous=NORMAL")
con.execute(
    """CREATE TABLE messages (
           id         INTEGER PRIMARY KEY,
           chat_id    INTEGER NOT NULL,
           sender_id  INTEGER NOT NULL,
           body       TEXT NOT NULL,
           created_at INTEGER NOT NULL
       )"""
)
con.execute("CREATE INDEX idx_msg_chat_created ON messages(chat_id, created_at, id)")

N = 500_000
CHAT = 1
base = 1_700_000_000_000
rows = [
    (i, CHAT if i % 10 else 2, i % 200, "message body %d" % i, base + i * 100)
    for i in range(1, N + 1)
]
con.executemany("INSERT INTO messages VALUES (?,?,?,?,?)", rows)
con.commit()
con.execute("ANALYZE")
con.commit()
print("rows:", con.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
      "| in chat 1:", con.execute("SELECT COUNT(*) FROM messages WHERE chat_id=1").fetchone()[0])

PAGE = 50


def timed(fn, runs=21):
    s = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        s.append((time.perf_counter() - t0) * 1000)
    return round(statistics.median(s), 3)


def offset_page(page_no):
    return con.execute(
        "SELECT id, sender_id, body, created_at FROM messages WHERE chat_id=? "
        "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        (CHAT, PAGE, page_no * PAGE),
    ).fetchall()


def keyset_page(cursor):
    if cursor is None:
        return con.execute(
            "SELECT id, sender_id, body, created_at FROM messages WHERE chat_id=? "
            "ORDER BY created_at DESC, id DESC LIMIT ?", (CHAT, PAGE)).fetchall()
    ca, cid = cursor
    return con.execute(
        "SELECT id, sender_id, body, created_at FROM messages WHERE chat_id=? "
        "AND (created_at, id) < (?, ?) ORDER BY created_at DESC, id DESC LIMIT ?",
        (CHAT, ca, cid, PAGE)).fetchall()


print("\n-- plan: OFFSET deep page")
for r in con.execute(
        "EXPLAIN QUERY PLAN SELECT id,sender_id,body,created_at FROM messages "
        "WHERE chat_id=? ORDER BY created_at DESC, id DESC LIMIT 50 OFFSET 100000", (CHAT,)):
    print("  ", r)
print("-- plan: keyset page")
for r in con.execute(
        "EXPLAIN QUERY PLAN SELECT id,sender_id,body,created_at FROM messages "
        "WHERE chat_id=? AND (created_at,id)<(?,?) ORDER BY created_at DESC, id DESC LIMIT 50",
        (CHAT, base + 100, 1)):
    print("  ", r)

PAGES = (0, 20, 200, 1000)
res = {}
for p in PAGES:
    res[("offset", p)] = timed(lambda p=p: offset_page(p))


def walk(pages):
    cur = None
    for _ in range(pages):
        out = keyset_page(cur)
        if not out:
            return None
        cur = (out[-1][3], out[-1][0])
    return cur


for p in PAGES:
    cur = walk(p)
    res[("keyset", p)] = timed(lambda c=cur: keyset_page(c))

print("\nrows scanned (page#*50)   offset_ms   keyset_ms")
for p in PAGES:
    print(f"{p*PAGE:>8d}-{p*PAGE+PAGE-1:<8d}      {res[('offset',p)]:8.3f}   {res[('keyset',p)]:8.3f}")

nonempty_o = all(offset_page(p) for p in PAGES)
nonempty_k = all(keyset_page(walk(p)) for p in PAGES)
print("all pages non-empty:", nonempty_o, nonempty_k)

# ---- ordering stability demo -----------------------------------------------
con.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, body TEXT)")
for i in range(1, 11):
    con.execute("INSERT INTO demo(body) VALUES (?)", ("m%d" % i,))
con.commit()
p1 = [r[0] for r in con.execute("SELECT id FROM demo ORDER BY id DESC LIMIT 3")]
con.execute("INSERT INTO demo(body) VALUES ('new')")   # new message arrives at the head
con.commit()
p2 = [r[0] for r in con.execute("SELECT id FROM demo ORDER BY id DESC LIMIT 3 OFFSET 3")]
p2k = [r[0] for r in con.execute(
    "SELECT id FROM demo WHERE id < ? ORDER BY id DESC LIMIT 3", (p1[-1],))]
print("\nstability demo (new row inserted between the two page fetches)")
print("  page1 offset0 :", p1)
print("  page2 offset3 :", p2, "| repeats page1 row:", bool(set(p2) & set(p1)), "| missed:", sorted(set(range(min(p1),max(p1)+1)) - set(p1) - set(p2)))
print("  page2 keyset  :", p2k, "| overlap with page1:", bool(set(p2k) & set(p1)))
con.close()
