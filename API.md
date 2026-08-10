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

## Files & Images

图片上传和附件管理，用于富文本编辑器中内嵌图片的存储与跨设备同步。

### Data Model: Attachment

```json
{
  "attachId": "a1b2c3...",
  "noteId": "n1",
  "type": 0,
  "fileName": "photo.jpg",
  "fileId": "f_abc123",
  "width": 1920,
  "height": 1080,
  "md5": "d41d8cd9...",
  "url": "",
  "state": 0,
  "createdAt": "2026-08-01T10:00:00Z"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| attachId | string | 附件唯一标识 (UUID) |
| noteId | string | 所属笔记 ID |
| type | int | `0` = 图片, `1` = 手写, `2` = 语音 |
| fileName | string | 原始文件名 |
| fileId | string | 服务端文件标识 |
| width | int | 图片宽度 (px) |
| height | int | 图片高度 (px) |
| md5 | string | 文件 MD5，空字符串 = 待同步 |
| url | string | 空 = 仅本地待上传, 非空 = 已同步的服务端 fileId |
| state | int | `0` = NEW, `1` = SYNCED, `2` = MODIFIED |
| createdAt | string | ISO 8601 创建时间 |

---

### POST /api/files/upload

上传图片文件到服务器。需要认证。

```
POST /api/files/upload
Authorization: Bearer xxx
Content-Type: multipart/form-data

file: (binary image data)
noteId: n1  (可选)
```

Response:
```json
{
  "code": 0,
  "data": {
    "fileId": "f_abc123",
    "url": "https://cdn.example.com/f_abc123.webp",
    "width": 1920,
    "height": 1080,
    "md5": "d41d8cd98f00b204e9800998ecf8427e"
  }
}
```

| 约束 | 值 |
|------|-----|
| 最大文件大小 | 10 MB |
| 支持格式 | JPEG, PNG, GIF, WebP |
| 超时 | 60s |

---

### GET /api/attachments/:attachId/download

下载附件图片。返回二进制流，`Content-Type` 为实际图片类型。

> 前端可通过 `getAttachmentDownloadUrl(attachId)` 获取完整 URL 直接用于 `<img src>`。

---

### GET /api/notes/:id/attachments

获取笔记的所有附件列表。需要认证。

```
GET /api/notes/n1/attachments
```

Response:
```json
{
  "code": 0,
  "data": [
    {
      "attachId": "a1b2c3...",
      "noteId": "n1",
      "type": 0,
      "fileName": "photo.jpg",
      "fileId": "f_abc123",
      "width": 1920,
      "height": 1080,
      "md5": "d41d8cd9...",
      "state": 1,
      "createdAt": "2026-08-01T10:00:00Z"
    }
  ]
}
```

---

### PUT /api/attachments/:attachId

更新附件元数据（同步后写回 md5/fileId）。需要认证。

```
PUT /api/attachments/a1b2c3...
Content-Type: application/json

{ "md5": "d41d8cd9...", "state": 1 }
```

---

### DELETE /api/attachments/:attachId

删除笔记中的附件（同时删除服务器文件）。需要认证。

```
DELETE /api/attachments/a1b2c3...
```

---

### 同步决策流程

```
for each Attachment where md5 == "":
  if url == "" → POST /api/files/upload     (上传)
  if url != "" → GET /attachments/:id/download  (下载)
              → PUT /attachments/:id         (写回 md5)
```

---

## Text Color

文字颜色不通过独立 API 传输，而是**内联在笔记 content 中**。使用 CSS 变量名存储，支持浅/深色模式自动切换。

### 颜色预设

| CSS 变量 | 浅色模式 | 深色模式 |
|---------|---------|---------|
| `--blueColor` | `#1A73E8` | `#8AB4F8` |
| `--redColor` | `#EA4335` | `#F28B82` |
| `--greenColor` | `#34A853` | `#81C995` |
| `--orangeColor` | `#FB9600` | `#FDD663` |
| `--yellowColor` | `#F9AB00` | `#FDE293` |
| `--grayColor` | `#5F6368` | `#BDC1C6` |

### 存储格式 (Markdown 内联 HTML)

```markdown
这是<span style="color: var(--blueColor)">蓝色文字</span>，后面正常。
```

### 前端 API

```js
// api/index.js
uploadFile(file, noteId)              → POST   /files/upload
getAttachmentDownloadUrl(attachId)    → 返回下载 URL 字符串
getNoteAttachments(noteId)            → GET    /notes/:id/attachments
updateAttachment(attachId, data)      → PUT    /attachments/:id
deleteAttachment(attachId)            → DELETE /attachments/:id
```

> 文字颜色不需要额外 API — 内容本身已携带颜色信息，随 `PUT /api/notes/:id` 的 content 字段一同持久化。

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
