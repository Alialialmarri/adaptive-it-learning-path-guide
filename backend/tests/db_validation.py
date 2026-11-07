"""Database validation report (read-only).

Usage (from the backend folder, after the app has run at least once and some
users have registered / studied / chatted):

    python tests/db_validation.py sql_app.db > tests/results/db_validation.txt

Prints counts, referential-integrity checks, per-user ownership checks and a
masked sample of rows. Password hashes and e-mail addresses are never printed.
Optionally reports the number of vector chunks per module in ./chroma_db.
"""
import os
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else "sql_app.db"
if not os.path.exists(DB):
    sys.exit(f"Database file not found: {DB}")

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = con.cursor()


def q(sql, args=()):
    return cur.execute(sql, args).fetchall()


def mask(text):
    text = str(text or "")
    return text[:2] + "***" if len(text) > 2 else "***"


print("=== 1. Row counts ===")
tables = [r[0] for r in q("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
for t in tables:
    print(f"{t:24s} {q(f'SELECT COUNT(*) FROM {t}')[0][0]}")

print("\n=== 2. Referential integrity (expected 0 orphans each) ===")
checks = {
    "user_progress -> users": "SELECT COUNT(*) FROM user_progress WHERE user_id NOT IN (SELECT id FROM users)",
    "user_progress -> modules": "SELECT COUNT(*) FROM user_progress WHERE module_id NOT IN (SELECT id FROM modules)",
    "lesson_progress -> users": "SELECT COUNT(*) FROM lesson_progress WHERE user_id NOT IN (SELECT id FROM users)",
    "lesson_progress -> lessons": "SELECT COUNT(*) FROM lesson_progress WHERE lesson_id NOT IN (SELECT id FROM lessons)",
    "chat_messages -> users": "SELECT COUNT(*) FROM chat_messages WHERE user_id NOT IN (SELECT id FROM users)",
    "chat_messages -> modules": "SELECT COUNT(*) FROM chat_messages WHERE module_id IS NOT NULL AND module_id NOT IN (SELECT id FROM modules)",
    "lessons -> modules": "SELECT COUNT(*) FROM lessons WHERE module_id NOT IN (SELECT id FROM modules)",
    "modules -> tracks": "SELECT COUNT(*) FROM modules WHERE track_id NOT IN (SELECT id FROM tracks)",
    "diagnostic_attempts -> users": "SELECT COUNT(*) FROM diagnostic_attempts WHERE user_id NOT IN (SELECT id FROM users)",
    "diagnostic_answers -> attempts": "SELECT COUNT(*) FROM diagnostic_answers WHERE attempt_id NOT IN (SELECT id FROM diagnostic_attempts)",
    "topic_mastery -> users": "SELECT COUNT(*) FROM topic_mastery WHERE user_id NOT IN (SELECT id FROM users)",
}
for name, sql in checks.items():
    try:
        print(f"{name:34s} orphans = {q(sql)[0][0]}")
    except sqlite3.Error as exc:
        print(f"{name:34s} could not run: {exc}")

print("\n=== 3. Credential storage ===")
total, hashed, plain_like = q(
    "SELECT COUNT(*), SUM(hashed_password LIKE '$2%'), SUM(hashed_password NOT LIKE '$2%') FROM users"
)[0]
print(f"users={total}, bcrypt-format hashes={hashed}, other format={plain_like}")
print("duplicate usernames:", q("SELECT COUNT(*) FROM (SELECT username FROM users GROUP BY username HAVING COUNT(*)>1)")[0][0])
print("duplicate e-mails  :", q("SELECT COUNT(*) FROM (SELECT email FROM users GROUP BY email HAVING COUNT(*)>1)")[0][0])

print("\n=== 4. Records per user (usernames masked) ===")
print(f"{'user':8s} {'user_progress':>13s} {'lessons_done':>12s} {'chat_msgs':>9s} {'diag_attempts':>13s}")
for uid, uname in q("SELECT id, username FROM users ORDER BY id"):
    up = q("SELECT COUNT(*) FROM user_progress WHERE user_id=?", (uid,))[0][0]
    lp = q("SELECT COUNT(*) FROM lesson_progress WHERE user_id=? AND completed=1", (uid,))[0][0]
    cm = q("SELECT COUNT(*) FROM chat_messages WHERE user_id=?", (uid,))[0][0]
    da = q("SELECT COUNT(*) FROM diagnostic_attempts WHERE user_id=?", (uid,))[0][0]
    print(f"{mask(uname):8s} {up:13d} {lp:12d} {cm:9d} {da:13d}")

print("\n=== 5. Chat ownership: each message belongs to exactly one user and one module ===")
print("messages without user  :", q("SELECT COUNT(*) FROM chat_messages WHERE user_id IS NULL")[0][0])
print("messages without module:", q("SELECT COUNT(*) FROM chat_messages WHERE module_id IS NULL")[0][0])
print("role values            :", q("SELECT role, COUNT(*) FROM chat_messages GROUP BY role"))

print("\n=== 6. Progress consistency: completed modules must have every lesson completed ===")
rows = q(
    """SELECT up.user_id, up.module_id,
              (SELECT COUNT(*) FROM lessons l WHERE l.module_id = up.module_id) AS total,
              (SELECT COUNT(*) FROM lesson_progress lp JOIN lessons l ON l.id = lp.lesson_id
                 WHERE lp.user_id = up.user_id AND l.module_id = up.module_id AND lp.completed = 1) AS done
       FROM user_progress up WHERE up.status = 'completed'"""
)
bad = [r for r in rows if r[2] != r[3]]
print(f"completed modules checked={len(rows)}, inconsistent={len(bad)}")

print("\n=== 7. Learning content stored (documents used for RAG) ===")
for mid, title, n in q("SELECT m.id, m.title, COUNT(l.id) FROM modules m LEFT JOIN lessons l ON l.module_id=m.id GROUP BY m.id ORDER BY m.id"):
    chars = q("SELECT COALESCE(SUM(LENGTH(content)),0) FROM lessons WHERE module_id=?", (mid,))[0][0]
    print(f"module {mid} '{title}': {n} lessons, {chars} characters of lesson text")

print("\n=== 8. Vector store (ChromaDB) chunks per module_id ===")
try:
    import chromadb

    client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(os.path.abspath(DB)), "chroma_db"))
    for coll in client.list_collections():
        c = client.get_collection(coll.name if hasattr(coll, "name") else coll)
        metas = c.get(include=["metadatas"])["metadatas"]
        per = {}
        for m in metas:
            per[m.get("module_id")] = per.get(m.get("module_id"), 0) + 1
        print(f"collection '{c.name}': {len(metas)} chunks, per module_id = {per}")
except Exception as exc:  # chroma not installed / folder missing
    print("skipped:", exc)
con.close()
