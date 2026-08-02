import json, urllib.request, urllib.error, os, sys

BASE = "http://localhost:5000"
headers_base = {"Content-Type": "application/json"}
passed = 0
failed = 0

def req(method, path, data=None, headers=None):
    h = dict(headers_base)
    if headers:
        h.update(headers)
    body = json.dumps(data).encode("utf-8") if data else None
    r = urllib.request.Request(f"{BASE}{path}", data=body, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(r)
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))

def ok(r, label=""):
    global passed, failed
    is_ok = r.get("code") == 0
    if is_ok:
        passed += 1
    else:
        failed += 1
    print(f"  [{'PASS' if is_ok else 'FAIL'}] {label}: {r.get('msg','')}")
    return r

print("=== Auth ===")
r = req("POST", "/api/auth/login", {"username": "testuser", "password": "123456"})
r = ok(r, "login")
token = r["data"]["token"]
auth = {"Authorization": f"Bearer {token}"}

r = req("GET", "/api/auth/me", headers=auth)
ok(r, "me")

print("=== Notebooks ===")
r = req("POST", "/api/notebooks", {"name": "Work", "color": "#4A90D9"}, headers=auth)
ok(r, "create notebook")
nb_id = r["data"]["id"]

r = req("GET", "/api/notebooks", headers=auth)
ok(r, f"list notebooks (count={len(r['data'])})")

r = req("PUT", f"/api/notebooks/{nb_id}", {"name": "Work Updated"}, headers=auth)
ok(r, "update notebook")

print("=== Notes ===")
for i in range(5):
    r = req("POST", "/api/notes", {"title": f"Note {i}", "content": f"Content {i}" * 20, "notebookId": nb_id, "color": "blue"}, headers=auth)
    ok(r, f"create note {i}")

r = req("GET", "/api/notes?page=1&size=20", headers=auth)
ok(r, f"list notes (total={r['pagination']['total']})")
first_id = r["data"][0]["id"]

r = req("GET", f"/api/notes/{first_id}", headers=auth)
ok(r, "get single note")

r = req("PUT", f"/api/notes/{first_id}", {"title": "Updated Title"}, headers=auth)
ok(r, "update note (no lock)")
updated_at = r["data"]["updatedAt"]

r = req("PUT", f"/api/notes/{first_id}", {"title": "Title v2"}, headers={**auth, "If-Match": updated_at})
ok(r, "update note (with lock)")

r = req("PUT", f"/api/notes/{first_id}", {"title": "Conflict"}, headers={**auth, "If-Match": "2020-01-01T00:00:00Z"})
is_conflict = r.get("code") == 409
if is_conflict:
    passed += 1
else:
    failed += 1
print(f"  [{'PASS' if is_conflict else 'FAIL'}] conflict detection")

r = req("PUT", f"/api/notes/{first_id}/pin", headers=auth)
ok(r, "pin toggle")

r = req("DELETE", f"/api/notes/{first_id}", headers=auth)
ok(r, "delete to trash")

r = req("GET", "/api/notes/trash", headers=auth)
ok(r, f"list trash (count={len(r['data'])})")

r = req("PUT", f"/api/notes/{first_id}/recover", headers=auth)
ok(r, "recover from trash")

r = req("DELETE", f"/api/notebooks/{nb_id}", headers=auth)
ok(r, "delete notebook")

print("=== Sync ===")
r = req("GET", "/api/notes/sync?since=2020-01-01T00:00:00Z", headers=auth)
ok(r, f"sync (updated={len(r['data']['updated'])}, deleted={len(r['data']['deletedIds'])})")

print("=== Share Settings ===")
r = req("GET", "/api/settings/share", headers=auth)
ok(r, "get share settings (default)")

r = req("PUT", "/api/settings/share", {"logoText": "My Custom Logo"}, headers=auth)
ok(r, "update share settings (partial)")

r = req("GET", "/api/settings/share", headers=auth)
is_partial = r["data"]["logoText"] == "My Custom Logo" and r["data"]["watermark"] == "\u5907\u5fd8\u5f55"
if is_partial:
    passed += 1
else:
    failed += 1
print(f"  [{'PASS' if is_partial else 'FAIL'}] verify partial update")

print("=== Pagination ===")
r = req("GET", "/api/notes?page=1&size=3", headers=auth)
ok(r, f"pagination (total={r['pagination']['total']}, pages={r['pagination']['totalPages']})")

print("=== Search ===")
r = req("GET", "/api/notes?keyword=Updated", headers=auth)
ok(r, f"search (found={r['pagination']['total']})")

print("=== Auth Refresh ===")
rt = req("POST", "/api/auth/login", {"username": "testuser", "password": "123456"})["data"]["refreshToken"]
r = req("POST", "/api/auth/refresh", {"refreshToken": rt})
ok(r, "refresh token")

print("=== Health ===")
r = req("GET", "/api/health")
ok(r, "health check")

print("=== Cold Backup ===")
backup_dir = r"E:\PyCharmProjects\mock-server\backup\testuser"
files = os.listdir(backup_dir) if os.path.isdir(backup_dir) else []
is_bk = len(files) >= 5
if is_bk:
    passed += 1
else:
    failed += 1
print(f"  [{'PASS' if is_bk else 'FAIL'}] backup files count: {len(files)}")

print(f"\n=== Results: {passed} passed, {failed} failed ===")
