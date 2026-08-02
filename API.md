# OPPO Sticky Notes API Documentation

Base URL: `http://localhost:5000/api`

## Common Response Format

```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

| Field | Type | Description |
|-------|------|-------------|
| code | int | 0 = success, non-zero = error |
| msg | string | Status message |
| data | object/array | Response payload |

For paginated list endpoints, the response includes additional `pagination` fields.

---

## Authentication

All note/notebook endpoints require `Authorization: Bearer <access_token>` header.

Access tokens expire after **1 hour**. Refresh tokens expire after **7 days**.

### POST /api/auth/register

Create a new account.

```
POST /api/auth/register
Content-Type: application/json

{ "username": "allen", "password": "123456" }
```

Response:
```json
{
  "code": 0,
  "msg": "success",
  "data": { "username": "allen" }
}
```

### POST /api/auth/login

Login and receive tokens.

```
POST /api/auth/login
{ "username": "allen", "password": "123456" }
```

Response:
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "token": "a1b2c3...",
    "refreshToken": "d4e5f6...",
    "expiresIn": 3600,
    "user": { "username": "allen", "createdAt": "2026-07-28T10:00:00Z" }
  }
}
```

| Field | Description |
|-------|-------------|
| token | Access token (Bearer), expires in 1 hour |
| refreshToken | Used to obtain a new access token, expires in 7 days |
| expiresIn | Access token TTL in seconds |

### POST /api/auth/refresh

Get a new access token using the refresh token. This invalidates the old token pair.

```
POST /api/auth/refresh
{ "refreshToken": "d4e5f6..." }
```

Response (same structure as login):
```json
{
  "code": 0,
  "data": {
    "token": "new-access...",
    "refreshToken": "new-refresh...",
    "expiresIn": 3600
  }
}
```

### GET /api/auth/me

Get current user info. Requires auth.

Response:
```json
{
  "code": 0,
  "data": { "username": "allen", "createdAt": "2026-07-28T10:00:00Z" }
}
```

### POST /api/auth/logout

Invalidate current token pair. Requires auth.

---

## Data Models

### Note

```json
{
  "id": "n1",
  "title": "Weekly Meeting Notes",
  "content": "# Meeting\n\n- item 1\n- item 2",
  "notebookId": "nb1",
  "color": "blue",
  "isPinned": true,
  "version": 3,
  "createdAt": "2026-07-20T09:00:00Z",
  "updatedAt": "2026-07-27T15:30:00Z",
  "deletedAt": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| title | string | Note title (max 100 chars) |
| content | string | Note content in **Markdown** format |
| notebookId | string/null | Associated notebook ID |
| color | string | `blue` / `green` / `yellow` / `orange` / `red` / `gray` |
| isPinned | boolean | Pinned to top |
| version | int | Monotonic version, incremented on every write. Used for offline merge detection |
| createdAt | string | ISO 8601 creation timestamp |
| updatedAt | string | ISO 8601 last update timestamp. **Also used as optimistic lock key** |
| deletedAt | string/null | ISO 8601 deletion timestamp |

### Notebook

```json
{
  "id": "nb1",
  "name": "Work",
  "color": "#4A90D9",
  "createdAt": "2026-07-01T10:00:00Z"
}
```

---

## Notebooks

### GET /api/notebooks

List all notebooks for current user.

### POST /api/notebooks

Create a notebook. Body: `{ "name": "Travel", "color": "#F5A623" }`

### PUT /api/notebooks/:id

Update a notebook.

### DELETE /api/notebooks/:id

Delete a notebook. Notes in this notebook get `notebookId` set to null.

---

## Notes

### GET /api/notes

Paginated list of non-deleted notes.

| Query Parameter | Type | Default | Description |
|-----------------|------|---------|-------------|
| page | int | 1 | Page number |
| size | int | 20 | Items per page (max 100) |
| sortBy | string | updatedAt | `updatedAt` or `createdAt` |
| keyword | string | — | Search in title and content |
| notebookId | string | — | Filter by notebook |
| color | string | — | Filter by color |

Response:
```json
{
  "code": 0,
  "msg": "success",
  "data": [ /* Note[] */ ],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 45,
    "totalPages": 3
  }
}
```

Notes are sorted: pinned first, then by `sortBy` descending.

### GET /api/notes/sync

**Incremental sync** — returns only notes changed since the given timestamp. Designed for mobile/desktop sync after reconnect.

| Query Parameter | Type | Description |
|-----------------|------|-------------|
| since | string | ISO 8601 timestamp. Return items with `updatedAt > since` |

Response:
```json
{
  "code": 0,
  "data": {
    "updated": [ /* Note[] — notes modified since `since` */ ],
    "deletedIds": [ "n1", "n2" ],
    "serverTime": "2026-07-28T12:00:00Z"
  }
}
```

**Sync flow:**
1. Client stores `lastSyncTime` locally
2. Calls `GET /api/notes/sync?since=<lastSyncTime>`
3. Merges `updated` into local cache
4. Removes notes in `deletedIds` from local cache
5. Stores new `serverTime` as `lastSyncTime`

### GET /api/notes/:id

Get a single note.

### POST /api/notes

Create a new note.

```json
{
  "title": "New Note",
  "content": "# Hello\n\nThis is **markdown**.",
  "notebookId": "nb1",
  "color": "yellow",
  "isPinned": false
}
```

### PUT /api/notes/:id

Update a note. Supports **optimistic locking** via `If-Match` header.

```
PUT /api/notes/n1
Authorization: Bearer xxx
If-Match: 2026-07-27T15:30:00Z
Content-Type: application/json

{ "title": "Updated Title", "content": "New content" }
```

**Conflict detection:** If `If-Match` does not equal the server's current `updatedAt`, the server returns:

```
HTTP 409 Conflict
{
  "code": 409,
  "msg": "Conflict: note was modified by another device. Server version: 2026-07-28T10:00:00Z"
}
```

The client should:
1. Re-fetch the latest note
2. Let the user merge changes
3. Retry with the new `updatedAt`

If `If-Match` is not provided, the update is always accepted (last-write-wins).

### DELETE /api/notes/:id

Move a note to trash.

### PUT /api/notes/:id/pin

Toggle pin status.

---

## Trash

### GET /api/notes/trash

List all deleted notes.

### PUT /api/notes/:id/recover

Recover a note from trash.

### DELETE /api/notes/:id/permanent

Permanently delete a note from trash.

---

## Health Check

### GET /api/health

```json
{ "status": "ok" }
```

---

## Share Settings

跨设备同步的用户分享设置。

### GET /api/settings/share

获取当前用户的分享页脚自定义文本。需要认证。

Response:
```json
{
  "code": 0,
  "data": {
    "logoText": "分享来自 Open Note",
    "watermark": "备忘录"
  }
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| logoText | string | `"分享来自 Open Note"` | 分享图片页脚第一行署名 |
| watermark | string | `"备忘录"` | 分享图片页脚第二行水印 |

### PUT /api/settings/share

更新分享设置。仅需发送要变更的字段，未提供的保留原值。

```
PUT /api/settings/share
Authorization: Bearer xxx
Content-Type: application/json

{ "logoText": "来自 allen 的分享" }
```

Response:
```json
{
  "code": 0,
  "data": {
    "logoText": "来自 allen 的分享",
    "watermark": "备忘录"
  }
}
```

### 前端集成

```
src/api/index.js
  getShareSettingsAPI()          → GET  /settings/share
  updateShareSettingsAPI(data)   → PUT  /settings/share

src/config/shareSettings.js
  getShareSettings()             → 调用 API，失败回退 localStorage
  getShareSettingsCached()       → 同步读取 localStorage 缓存（即时展示用）
  saveShareSettings(partial)     → 先写 localStorage，再调 API 持久化
```

### 客户端容错策略

```
读取：  API 成功 → 写入 localStorage 缓存 → 返回
       API 失败 → 从 localStorage 读取 → 返回缓存值

写入：  localStorage 即时更新（UI 即时响应）
       API 调用后台静默同步
       API 失败 → 本地缓存生效，下次成功时自动覆盖
```

> 修改设置后需**重新点击分享按钮**以重新生成图片，页脚文字才会更新。

---

## Cross-Platform Notes

| Feature | Implementation |
|---------|---------------|
| **Pagination** | `?page=&size=` — mobile uses small page sizes, desktop uses larger |
| **Incremental Sync** | `GET /api/notes/sync?since=` — mobile fetches only changes after reconnect |
| **Token Refresh** | `POST /api/auth/refresh` — clients auto-refresh before token expiry |
| **Optimistic Lock** | `If-Match: <updatedAt>` header — 409 Conflict on concurrent edits |
| **Versioning** | `version` field on every note — clients track local version for offline merge |
| **Auto-refresh** | Axios interceptor detects 401 → calls `/auth/refresh` → retries |

## Running Locally

```bash
# Mock server
cd mock-server
pip install flask flask-cors
python server.py          # → http://localhost:5000

# Frontend
cd note-frontend
npm install
npm run dev                # → http://localhost:3000
```
