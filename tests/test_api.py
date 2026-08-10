import time
import pytest
import requests

BASE = "http://localhost:5000"


class TestHealth:
    """健康检查"""

    def test_health_ok(self):
        r = requests.get(f"{BASE}/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# 测试数据
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def ts():
    return str(int(time.time() * 1000))


@pytest.fixture(scope="session")
def test_user(ts):
    """注册一个新用户，返回用户名和密码"""
    username = f"test_user_{ts}"
    password = "test123"
    r = requests.post(f"{BASE}/api/auth/register",
                      json={"username": username, "password": password})
    assert r.json()["code"] == 0, f"注册失败: {r.json()}"
    return username, password


@pytest.fixture(scope="session")
def tokens(test_user):
    """登录普通用户，返回 token / refreshToken"""
    username, password = test_user
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"username": username, "password": password})
    data = r.json()
    assert data["code"] == 0, f"登录失败: {data}"
    return data["data"]["token"], data["data"]["refreshToken"]


@pytest.fixture(scope="session")
def auth_headers(tokens):
    token, _ = tokens
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_token():
    """获取 admin token"""
    r = requests.post(f"{BASE}/api/admin/login",
                      json={"password": "admin123"})
    data = r.json()
    assert data["code"] == 0, f"admin 登录失败: {data}"
    return data["data"]["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------------------------------------------------------------------------
# Auth — register
# ---------------------------------------------------------------------------

class TestAuthRegister:
    """POST /api/auth/register"""

    def test_register_success(self, ts):
        r = requests.post(f"{BASE}/api/auth/register",
                          json={"username": f"reg_{ts}", "password": "abc123"})
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert body["data"]["username"] == f"reg_{ts}"

    def test_register_username_too_short(self):
        r = requests.post(f"{BASE}/api/auth/register",
                          json={"username": "a", "password": "123abc"})
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_register_password_too_short(self):
        r = requests.post(f"{BASE}/api/auth/register",
                          json={"username": "abc", "password": "ab"})
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_register_missing_fields(self):
        r = requests.post(f"{BASE}/api/auth/register",
                          json={"username": "someone"})
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_register_duplicate(self, test_user):
        username, password = test_user
        r = requests.post(f"{BASE}/api/auth/register",
                          json={"username": username, "password": "123456"})
        assert r.status_code == 400
        assert r.json()["code"] != 0


# ---------------------------------------------------------------------------
# Auth — login
# ---------------------------------------------------------------------------

class TestAuthLogin:

    def test_login_success(self, test_user):
        username, password = test_user
        r = requests.post(f"{BASE}/api/auth/login",
                          json={"username": username, "password": password})
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        data = body["data"]
        assert "token" in data
        assert "refreshToken" in data
        assert data["expiresIn"] == 3600
        assert data["user"]["username"] == username

    def test_login_wrong_password(self, test_user):
        username, _ = test_user
        r = requests.post(f"{BASE}/api/auth/login",
                          json={"username": username, "password": "wrong"})
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_login_nonexistent_user(self):
        r = requests.post(f"{BASE}/api/auth/login",
                          json={"username": "no_such_user_xyz", "password": "123456"})
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_login_missing_fields(self):
        r = requests.post(f"{BASE}/api/auth/login",
                          json={"username": "someone"})
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_login_non_json_body(self):
        r = requests.post(f"{BASE}/api/auth/login",
                          data="not-a-json",
                          headers={"Content-Type": "text/plain"})
        assert r.status_code == 400
        assert r.json()["code"] != 0


# ---------------------------------------------------------------------------
# Auth — refresh
# ---------------------------------------------------------------------------

class TestAuthRefresh:

    def test_refresh_success(self, test_user):
        username, password = test_user
        login_r = requests.post(f"{BASE}/api/auth/login",
                                json={"username": username, "password": password})
        refresh = login_r.json()["data"]["refreshToken"]
        r = requests.post(f"{BASE}/api/auth/refresh",
                          json={"refreshToken": refresh})
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert "token" in body["data"]
        assert "refreshToken" in body["data"]

    def test_old_token_invalid_after_refresh(self, test_user):
        username, password = test_user
        login_r = requests.post(f"{BASE}/api/auth/login",
                                json={"username": username, "password": password})
        token = login_r.json()["data"]["token"]
        refresh = login_r.json()["data"]["refreshToken"]
        r = requests.post(f"{BASE}/api/auth/refresh",
                          json={"refreshToken": refresh})
        assert r.json()["code"] == 0
        r2 = requests.get(f"{BASE}/api/auth/me",
                          headers={"Authorization": f"Bearer {token}"})
        # old token should be invalid (刷新会删除旧的 access token)
        assert r2.json()["code"] != 0

    def test_refresh_wrong_token(self):
        r = requests.post(f"{BASE}/api/auth/refresh",
                          json={"refreshToken": "invalid_refresh_token"})
        assert r.json()["code"] != 0

    def test_refresh_expired_token(self):
        r = requests.post(f"{BASE}/api/auth/refresh",
                          json={"refreshToken": "long_expired_token_xyz"})
        assert r.json()["code"] != 0


# ---------------------------------------------------------------------------
# Auth — me
# ---------------------------------------------------------------------------

class TestAuthMe:

    def test_me_success(self, auth_headers, test_user):
        username, _ = test_user
        r = requests.get(f"{BASE}/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert body["data"]["username"] == username
        assert "createdAt" in body["data"]

    def test_me_no_token(self):
        r = requests.get(f"{BASE}/api/auth/me")
        assert r.status_code == 401
        assert r.json()["code"] == 401

    def test_me_wrong_token(self):
        r = requests.get(f"{BASE}/api/auth/me",
                         headers={"Authorization": "Bearer bad_token"})
        assert r.status_code == 401
        assert r.json()["code"] == 401


# ---------------------------------------------------------------------------
# Auth — logout
# ---------------------------------------------------------------------------

class TestAuthLogout:

    def test_logout_and_token_invalid(self, test_user):
        username, password = test_user
        r = requests.post(f"{BASE}/api/auth/login",
                          json={"username": username, "password": password})
        token = r.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}
        r2 = requests.post(f"{BASE}/api/auth/logout", headers=headers)
        assert r2.json()["code"] == 0
        r3 = requests.get(f"{BASE}/api/auth/me", headers=headers)
        assert r3.json()["code"] == 401


# ---------------------------------------------------------------------------
# Notebooks
# ---------------------------------------------------------------------------

class TestNotebooks:

    @pytest.fixture(scope="class")
    def nb_id(self, auth_headers):
        r = requests.post(f"{BASE}/api/notebooks",
                          json={"name": "Test NB", "color": "#4A90D9"},
                          headers=auth_headers)
        assert r.json()["code"] == 0
        return r.json()["data"]["id"]

    def test_list_empty(self, auth_headers):
        r = requests.get(f"{BASE}/api/notebooks", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["code"] == 0

    def test_create_notebook(self, auth_headers):
        r = requests.post(f"{BASE}/api/notebooks",
                          json={"name": "My Notebook", "color": "#FF0000"},
                          headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert body["data"]["name"] == "My Notebook"

    def test_create_notebook_empty_name(self, auth_headers):
        r = requests.post(f"{BASE}/api/notebooks",
                          json={"name": "", "color": "#000000"},
                          headers=auth_headers)
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_create_notebook_missing_fields(self, auth_headers):
        r = requests.post(f"{BASE}/api/notebooks",
                          json={}, headers=auth_headers)
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_update_notebook(self, auth_headers, nb_id):
        r = requests.put(f"{BASE}/api/notebooks/{nb_id}",
                         json={"name": "Updated NB", "color": "#00FF00"},
                         headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert body["data"]["name"] == "Updated NB"

    def test_update_notebook_not_found(self, auth_headers):
        r = requests.put(f"{BASE}/api/notebooks/nb_fake_id",
                         json={"name": "Nope"},
                         headers=auth_headers)
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_delete_notebook_nulls_notes(self, auth_headers):
        nb_r = requests.post(f"{BASE}/api/notebooks",
                             json={"name": "ToDelete"},
                             headers=auth_headers)
        nb_id = nb_r.json()["data"]["id"]
        note_r = requests.post(f"{BASE}/api/notes",
                               json={"title": "Note in NB",
                                     "notebookId": nb_id},
                               headers=auth_headers)
        note_id = note_r.json()["data"]["id"]
        r = requests.delete(f"{BASE}/api/notebooks/{nb_id}",
                            headers=auth_headers)
        assert r.json()["code"] == 0
        r2 = requests.get(f"{BASE}/api/notes/{note_id}", headers=auth_headers)
        assert r2.json()["code"] == 0
        assert r2.json()["data"]["notebookId"] is None

    def test_delete_notebook_not_found(self, auth_headers):
        r = requests.delete(f"{BASE}/api/notebooks/nb_fake_id",
                            headers=auth_headers)
        assert r.status_code == 400
        assert r.json()["code"] != 0


# ---------------------------------------------------------------------------
# Notes — CRUD
# ---------------------------------------------------------------------------

class TestNotes:

    @pytest.fixture(scope="class")
    def note_id(self, auth_headers):
        r = requests.post(f"{BASE}/api/notes",
                          json={"title": "CRUD Note",
                                "content": "Content here",
                                "color": "blue"},
                          headers=auth_headers)
        assert r.json()["code"] == 0
        return r.json()["data"]["id"]

    def test_create_note(self, auth_headers):
        r = requests.post(f"{BASE}/api/notes",
                          json={"title": "Hello", "content": "World"},
                          headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert body["data"]["title"] == "Hello"

    def test_create_note_empty_title_trim(self, auth_headers):
        r = requests.post(f"{BASE}/api/notes",
                          json={"title": "", "content": "test"},
                          headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["code"] == 0

    def test_list_notes(self, auth_headers):
        r = requests.get(f"{BASE}/api/notes", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert "pagination" in body
        pag = body["pagination"]
        assert "page" in pag
        assert "size" in pag
        assert "total" in pag
        assert "totalPages" in pag

    def test_list_pagination(self, auth_headers):
        r = requests.get(f"{BASE}/api/notes?page=1&size=2",
                         headers=auth_headers)
        assert r.status_code == 200
        pag = r.json()["pagination"]
        assert pag["page"] == 1
        assert pag["size"] == 2

    def test_list_filter_by_notebook(self, auth_headers):
        r = requests.get(f"{BASE}/api/notes?notebookId=nb_fake",
                         headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["code"] == 0

    def test_list_filter_by_color(self, auth_headers):
        r = requests.get(f"{BASE}/api/notes?color=blue",
                         headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["code"] == 0

    def test_list_keyword_search(self, auth_headers):
        r = requests.get(f"{BASE}/api/notes?keyword=CRUD",
                         headers=auth_headers)
        assert r.json()["code"] == 0

    def test_list_sort_by_createdAt(self, auth_headers):
        r = requests.get(f"{BASE}/api/notes?sortBy=createdAt",
                         headers=auth_headers)
        assert r.json()["code"] == 0

    def test_pinned_notes_first(self, auth_headers):
        r1 = requests.post(f"{BASE}/api/notes",
                           json={"title": "Pinned Note",
                                 "content": "pinned",
                                 "isPinned": True},
                           headers=auth_headers)
        assert r1.json()["code"] == 0
        pinned_id = r1.json()["data"]["id"]
        r2 = requests.get(f"{BASE}/api/notes?size=50",
                          headers=auth_headers)
        notes = r2.json()["data"]
        pinned = [n for n in notes if n["id"] == pinned_id]
        assert any(n["isPinned"] for n in pinned)

    def test_get_single_note(self, auth_headers, note_id):
        r = requests.get(f"{BASE}/api/notes/{note_id}",
                         headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["code"] == 0
        assert r.json()["data"]["id"] == note_id

    def test_get_note_not_found(self, auth_headers):
        r = requests.get(f"{BASE}/api/notes/n_fake_999",
                         headers=auth_headers)
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_update_note_no_lock(self, auth_headers, note_id):
        r = requests.put(f"{BASE}/api/notes/{note_id}",
                         json={"title": "No Lock Update"},
                         headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["code"] == 0

    def test_update_note_with_correct_if_match(self, auth_headers, note_id):
        r = requests.get(f"{BASE}/api/notes/{note_id}",
                         headers=auth_headers)
        updated_at = r.json()["data"]["updatedAt"]
        r2 = requests.put(f"{BASE}/api/notes/{note_id}",
                          json={"title": "Locked Update"},
                          headers={**auth_headers,
                                   "If-Match": updated_at})
        assert r2.status_code == 200
        assert r2.json()["code"] == 0

    def test_update_note_with_wrong_if_match(self, auth_headers, note_id):
        r2 = requests.put(f"{BASE}/api/notes/{note_id}",
                          json={"title": "Should Conflict"},
                          headers={**auth_headers,
                                   "If-Match": "2020-01-01T00:00:00Z"})
        assert r2.status_code == 409
        assert r2.json()["code"] == 409

    def test_sync_with_since(self, auth_headers):
        r = requests.get(f"{BASE}/api/notes/sync?since=2020-01-01T00:00:00Z",
                         headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert "updated" in body["data"]
        assert "deletedIds" in body["data"]
        assert "serverTime" in body["data"]

    def test_sync_without_since(self, auth_headers):
        r = requests.get(f"{BASE}/api/notes/sync", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert "updated" in body["data"]

    def test_delete_note_to_trash(self, auth_headers):
        r = requests.post(f"{BASE}/api/notes",
                          json={"title": "To Trash"},
                          headers=auth_headers)
        note_id = r.json()["data"]["id"]
        r2 = requests.delete(f"{BASE}/api/notes/{note_id}",
                             headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["code"] == 0
        r3 = requests.get(f"{BASE}/api/notes/trash",
                          headers=auth_headers)
        trash_ids = [n["id"] for n in r3.json()["data"]]
        assert note_id in trash_ids

    def test_trash_list(self, auth_headers):
        r = requests.get(f"{BASE}/api/notes/trash",
                         headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["code"] == 0

    def test_recover_from_trash(self, auth_headers):
        r = requests.post(f"{BASE}/api/notes",
                          json={"title": "Recover Me"},
                          headers=auth_headers)
        note_id = r.json()["data"]["id"]
        requests.delete(f"{BASE}/api/notes/{note_id}",
                        headers=auth_headers)
        r2 = requests.put(f"{BASE}/api/notes/{note_id}/recover",
                          headers=auth_headers)
        assert r2.json()["code"] == 0
        r3 = requests.get(f"{BASE}/api/notes/{note_id}",
                          headers=auth_headers)
        assert r3.json()["data"]["deletedAt"] is None

    def test_permanent_delete(self, auth_headers):
        r = requests.post(f"{BASE}/api/notes",
                          json={"title": "Permanent Me"},
                          headers=auth_headers)
        note_id = r.json()["data"]["id"]
        requests.delete(f"{BASE}/api/notes/{note_id}",
                        headers=auth_headers)
        r2 = requests.delete(f"{BASE}/api/notes/{note_id}/permanent",
                             headers=auth_headers)
        assert r2.json()["code"] == 0
        r3 = requests.get(f"{BASE}/api/notes/trash",
                          headers=auth_headers)
        trash_ids = [n["id"] for n in r3.json()["data"]]
        assert note_id not in trash_ids

    def test_permanent_delete_only_trash(self, auth_headers, note_id):
        r = requests.delete(f"{BASE}/api/notes/{note_id}/permanent",
                            headers=auth_headers)
        # 非回收站笔记不能永久删除
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_toggle_pin(self, auth_headers, note_id):
        r = requests.get(f"{BASE}/api/notes/{note_id}",
                         headers=auth_headers)
        was_pinned = r.json()["data"]["isPinned"]
        r2 = requests.put(f"{BASE}/api/notes/{note_id}/pin",
                          headers=auth_headers)
        assert r2.json()["code"] == 0
        assert r2.json()["data"]["isPinned"] == (not was_pinned)


# ---------------------------------------------------------------------------
# Share Settings
# ---------------------------------------------------------------------------

class TestShareSettings:

    def test_get_defaults(self, auth_headers):
        r = requests.get(f"{BASE}/api/settings/share",
                         headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        data = body["data"]
        assert "logoText" in data
        assert "watermark" in data

    def test_partial_update_logo_only(self, auth_headers):
        r = requests.put(f"{BASE}/api/settings/share",
                         json={"logoText": "Custom Logo"},
                         headers=auth_headers)
        assert r.json()["code"] == 0
        data = r.json()["data"]
        assert data["logoText"] == "Custom Logo"
        assert data["watermark"] != ""

    def test_full_update(self, auth_headers):
        r = requests.put(f"{BASE}/api/settings/share",
                         json={"logoText": "Logo Full",
                               "watermark": "WM Full"},
                         headers=auth_headers)
        assert r.json()["code"] == 0
        data = r.json()["data"]
        assert data["logoText"] == "Logo Full"
        assert data["watermark"] == "WM Full"


# ---------------------------------------------------------------------------
# Admin — login
# ---------------------------------------------------------------------------

class TestAdminLogin:

    def test_admin_login_success(self):
        r = requests.post(f"{BASE}/api/admin/login",
                          json={"password": "admin123"})
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert "token" in body["data"]
        assert body["data"]["expiresIn"] == 7200

    def test_admin_login_wrong_password(self):
        r = requests.post(f"{BASE}/api/admin/login",
                          json={"password": "wrong"})
        assert r.status_code == 401
        assert r.json()["code"] != 0

    def test_admin_login_empty_password(self):
        r = requests.post(f"{BASE}/api/admin/login",
                          json={"password": ""})
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_admin_login_non_json_body(self):
        r = requests.post(f"{BASE}/api/admin/login",
                          data="raw text",
                          headers={"Content-Type": "text/plain"})
        assert r.status_code == 400
        assert r.json()["code"] != 0


# ---------------------------------------------------------------------------
# Admin — stats
# ---------------------------------------------------------------------------

class TestAdminStats:

    def test_admin_stats(self, admin_headers):
        r = requests.get(f"{BASE}/api/admin/stats",
                         headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        data = body["data"]
        assert "userCount" in data
        assert "noteCount" in data
        assert "trashCount" in data
        assert "totalContentSize" in data


# ---------------------------------------------------------------------------
# Admin — users
# ---------------------------------------------------------------------------

class TestAdminUsers:

    def test_admin_users_list(self, admin_headers):
        r = requests.get(f"{BASE}/api/admin/users",
                         headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert "pagination" in body

    def test_admin_users_pagination(self, admin_headers):
        r = requests.get(f"{BASE}/api/admin/users?page=1&size=2",
                         headers=admin_headers)
        pag = r.json()["pagination"]
        assert pag["page"] == 1
        assert pag["size"] == 2

    def test_admin_users_keyword_search(self, admin_headers, test_user):
        username, _ = test_user
        r = requests.get(f"{BASE}/api/admin/users?keyword={username}",
                         headers=admin_headers)
        assert r.json()["code"] == 0
        users = r.json()["data"]
        assert any(u["username"] == username for u in users)

    def test_admin_create_user(self, admin_headers, ts):
        r = requests.post(f"{BASE}/api/admin/users",
                          json={"username": f"admin_created_{ts}",
                                "password": "pass123"},
                          headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert body["data"]["username"] == f"admin_created_{ts}"
        assert body["data"]["noteCount"] == 0

    def test_admin_create_user_duplicate(self, admin_headers, test_user):
        username, _ = test_user
        r = requests.post(f"{BASE}/api/admin/users",
                          json={"username": username, "password": "123456"},
                          headers=admin_headers)
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_admin_create_user_short_username(self, admin_headers):
        r = requests.post(f"{BASE}/api/admin/users",
                          json={"username": "a", "password": "123456"},
                          headers=admin_headers)
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_admin_create_user_short_password(self, admin_headers):
        r = requests.post(f"{BASE}/api/admin/users",
                          json={"username": "valid_user",
                                "password": "ab"},
                          headers=admin_headers)
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_admin_reset_password(self, admin_headers, test_user):
        username, _ = test_user
        r = requests.get(f"{BASE}/api/admin/users?keyword={username}",
                         headers=admin_headers)
        users = r.json()["data"]
        user_id = next(u["id"] for u in users if u["username"] == username)
        r2 = requests.put(f"{BASE}/api/admin/users/{user_id}/password",
                          json={"password": "newpass123"},
                          headers=admin_headers)
        assert r2.json()["code"] == 0

    def test_admin_reset_password_user_not_found(self, admin_headers):
        r = requests.put(f"{BASE}/api/admin/users/99999/password",
                         json={"password": "newpass123"},
                         headers=admin_headers)
        assert r.status_code == 400
        assert r.json()["code"] != 0

    def test_admin_reset_password_too_short(self, admin_headers, test_user):
        username, _ = test_user
        r = requests.get(f"{BASE}/api/admin/users?keyword={username}",
                         headers=admin_headers)
        users = r.json()["data"]
        user_id = next(u["id"] for u in users if u["username"] == username)
        r2 = requests.put(f"{BASE}/api/admin/users/{user_id}/password",
                          json={"password": "a"},
                          headers=admin_headers)
        assert r2.json()["code"] != 0

    def test_admin_delete_user(self, admin_headers, ts):
        r = requests.post(f"{BASE}/api/admin/users",
                          json={"username": f"to_delete_{ts}",
                                "password": "pass123"},
                          headers=admin_headers)
        user_id = r.json()["data"]["id"]
        r2 = requests.delete(f"{BASE}/api/admin/users/{user_id}",
                             headers=admin_headers)
        assert r2.json()["code"] == 0

    def test_admin_delete_user_not_found(self, admin_headers):
        r = requests.delete(f"{BASE}/api/admin/users/99999",
                            headers=admin_headers)
        assert r.status_code == 400
        assert r.json()["code"] != 0


# ---------------------------------------------------------------------------
# Admin — notes
# ---------------------------------------------------------------------------

class TestAdminNotes:

    def test_admin_notes_list(self, admin_headers):
        r = requests.get(f"{BASE}/api/admin/notes",
                         headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert "pagination" in body

    def test_admin_notes_filter_by_user(self, admin_headers, test_user):
        username, _ = test_user
        r = requests.get(f"{BASE}/api/admin/users?keyword={username}",
                         headers=admin_headers)
        user_id = next(u["id"] for u in r.json()["data"]
                       if u["username"] == username)
        r2 = requests.get(f"{BASE}/api/admin/notes?userId={user_id}",
                          headers=admin_headers)
        assert r2.json()["code"] == 0

    def test_admin_notes_include_trash(self, admin_headers):
        r = requests.get(f"{BASE}/api/admin/notes?includeTrash=true",
                         headers=admin_headers)
        assert r.json()["code"] == 0

    def test_admin_notes_keyword_search(self, admin_headers):
        r = requests.get(f"{BASE}/api/admin/notes?keyword=test",
                         headers=admin_headers)
        assert r.json()["code"] == 0

    def test_admin_notes_pagination(self, admin_headers):
        r = requests.get(f"{BASE}/api/admin/notes?page=1&size=5",
                         headers=admin_headers)
        assert r.json()["pagination"]["size"] == 5

    def test_admin_delete_note(self, admin_headers, ts):
        username = f"admin_del_{ts}"
        password = "pass123"
        r0 = requests.post(f"{BASE}/api/admin/users",
                           json={"username": username, "password": password},
                           headers=admin_headers)
        assert r0.json()["code"] == 0
        login_r = requests.post(f"{BASE}/api/auth/login",
                                json={"username": username, "password": password})
        user_token = login_r.json()["data"]["token"]
        user_auth = {"Authorization": f"Bearer {user_token}"}
        r = requests.post(f"{BASE}/api/notes",
                          json={"title": "AdminDelete"},
                          headers=user_auth)
        assert r.json()["code"] == 0
        note_id = r.json()["data"]["id"]
        r2 = requests.delete(f"{BASE}/api/admin/notes/{note_id}",
                             headers=admin_headers)
        assert r2.json()["code"] == 0


# ---------------------------------------------------------------------------
# 权限 & 边界
# ---------------------------------------------------------------------------

class TestPermissions:

    def test_unauthorized_no_token(self):
        endpoints = [
            ("GET", "/api/auth/me"),
            ("GET", "/api/notebooks"),
            ("GET", "/api/notes"),
            ("GET", "/api/settings/share"),
            ("GET", "/api/notes/trash"),
            ("GET", "/api/admin/stats"),
        ]
        for method, path in endpoints:
            r = requests.request(method, f"{BASE}{path}")
            assert r.status_code == 401, f"{method} {path} 应返回 401"

    def test_unauthorized_wrong_token(self):
        bad = {"Authorization": "Bearer wrong_token"}
        endpoints = [
            ("GET", "/api/auth/me"),
            ("GET", "/api/notebooks"),
            ("GET", "/api/notes"),
            ("GET", "/api/settings/share"),
            ("GET", "/api/admin/stats"),
        ]
        for method, path in endpoints:
            r = requests.request(method, f"{BASE}{path}", headers=bad)
            assert r.status_code == 401, f"{method} {path} 应返回 401"

    def test_normal_user_cannot_access_admin(self, auth_headers):
        admin_endpoints = [
            ("GET", "/api/admin/stats"),
            ("GET", "/api/admin/users"),
            ("GET", "/api/admin/notes"),
        ]
        for method, path in admin_endpoints:
            r = requests.request(method, f"{BASE}{path}",
                                 headers=auth_headers)
            assert r.status_code == 401, \
                f"普通用户不应能访问 {method} {path}"
