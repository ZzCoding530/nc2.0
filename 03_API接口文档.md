# V1 开发文档 03 · API 接口文档

> **Base URL**：`https://learn.<域名>/api`
> **本文与 FastAPI 自动生成的 `/docs`（OpenAPI）为准双向对照**：实现时以本文字段名为准，Pydantic schema 与本文不一致视为 bug。
> **读者**：前后端开发

---

## 1. 通用约定

- **认证**：`Authorization: Bearer <jwt>`。学员 token 与运营 token 使用不同签名 secret（`JWT_SECRET_STUDENT` / `JWT_SECRET_STAFF`），互不通用，payload 含 `scope: "student" | "staff"`。
- **时间格式**：一律 UTC ISO8601 字符串（`2026-10-10T12:00:00Z`），前端转北京时间展示。
- **分页**：V1 数据量小，学员端接口不分页；运营学员列表给 `page/page_size`（默认 1/50）。
- **错误结构**（HTTP 状态码 + 固定 body）：

```json
{ "error": { "code": "EMAIL_NOT_WHITELISTED", "message": "该邮箱未在开班名单中，请联系班主任" } }
```

### 1.1 错误码表

| code | HTTP | 场景 |
|---|---|---|
| INVALID_CREDENTIALS | 401 | 邮箱/密码错误（不区分哪个错） |
| ACCOUNT_PENDING | 403 | 未激活登录 |
| ACCOUNT_LOCKED | 429 | 连续 5 次失败锁 10 分钟 |
| EMAIL_NOT_WHITELISTED | 403 | 注册邮箱不在白名单 |
| EMAIL_TAKEN | 409 | 邮箱已注册 |
| TOKEN_INVALID / TOKEN_EXPIRED | 400 | 验证/重置链接无效或过期 |
| NOT_FOUND | 404 | 课时/资源不存在 |
| LESSON_LOCKED | 403 | 预习未到 T-2 |
| SCHEDULE_CONFLICT | 409 | 同学员同课时重复排期（正常走 upsert 不触发） |
| LINK_REQUIRED | 400 | 发预习邮件但上课链接为空 |
| FORBIDDEN | 403 | 越权（学员 token 访问 admin 接口等） |

## 2. 学员端 · 认证（auth）

### POST /auth/register
```json
// body
{ "email": "you@example.com", "name": "同学", "password": "Passw0rd!" }
```
- 校验：邮箱格式 / 密码 ≥8 位含字母数字 / 邮箱在 whitelist 且未被 used
- 动作：建 student（status=pending）→ 写 email_token(verify, 24h) → 发验证邮件 → 回填 whitelist.used_by
```json
// 200
{ "message": "验证邮件已发送，请 24 小时内激活" }
```

### POST /auth/verify/{token}
- 激活账号：status pending→active，token 置 used；成功即自动签发 JWT（免再登录）
```json
// 200
{ "token": "<jwt>", "student": { "id": 1, "name": "同学", "email": "you@example.com", "cohort": "202610 期" } }
```

### POST /auth/resend-verification
```json
{ "email": "you@example.com" }
```
- 60s 冷却；未注册邮箱同样返回成功（不泄露存在性）

### POST /auth/login
```json
{ "email": "you@example.com", "password": "Passw0rd!" }
// 200
{ "token": "<jwt>", "student": { "id": 1, "name": "同学", "email": "you@example.com", "cohort": "202610 期", "cohort_start_date": "2026-10-01" } }
```

### POST /auth/forgot-password → POST /auth/reset-password
```json
// forgot: { "email": "..." }  → 发重置邮件（24h token）
// reset:  { "token": "...", "new_password": "..." }  → 200 { "message": "密码已更新，请重新登录" }
```

### POST /auth/logout
- 前端清 token 即可；V1 无服务端黑名单（14 天过期足够）

### GET /me（需登录）
```json
{
  "student": { "id": 1, "name": "同学", "email": "you@example.com", "cohort": "202610 期" },
  "links": { "brush_sop_url": "https://...", "qa_contact": "qa@<域名>" }
}
```

## 3. 学员端 · 课程数据（只读 + 轻标记）

### GET /overview（学习台一次拉全）
```json
{
  "progress": {
    "one_on_one": { "done": 3, "total": 15 },
    "recorded":   { "done": 6, "total": 27 }
  },
  "next_lesson": {
    "code": "T01", "title": "Transformer 架构",
    "scheduled_at": "2026-10-10T12:00:00Z",
    "meeting_link": "https://meeting.tencent.com/d/xxx",
    "status": "preview",                  // preview | ready | null(未排)
    "preview_unlocked": true
  },
  "todos": [
    { "kind": "preview",   "lesson_code": "T01", "title": "预习 · 三问预写", "acted": false },
    { "kind": "recorded",  "part_group": "D-1",  "title": "录播 D01–D06 · 模型 API 工程", "done_count": 6, "total": 6, "acted": false }
  ]
}
```
- `next_lesson.status`：`preview`（T-2 已到未读）/ `ready`（其余已排状态）/ `null`（无排期，前端显示占位卡）

### GET /map（课程地图）
```json
{
  "modules": [
    {
      "code": "M1", "title": "CS 理论基础", "subtitle": "C01–C04 · 4 节 1v1",
      "lessons": [
        {
          "code": "C01", "title": "计算机网络", "type": "1v1",
          "display_status": "done",           // locked | preview | ready | done | pending
          "scheduled_at": "2026-10-03T12:00:00Z",
          "is_current": false
        }
      ]
    },
    { "code": "M4", "title": "AI Coding · 录播+验收", "lessons": [ /* 含 27 讲与 3 验收，part_group 分组由前端折叠 */ ] }
  ]
}
```
- `display_status` 推导规则（后端算好，前端不重复实现）：
  `done`←schedule.done；`preview`←scheduled 且 T-2 已到 且无 preview_read；`ready`←scheduled；`pending`←planned 未到解锁；`locked`←录播未开放部分（V1 全部开放，预留）

### GET /lessons/{code}（课时详情）
```json
{
  "code": "T01", "title": "Transformer 架构", "type": "1v1",
  "module_title": "AI 理论基础", "duration_min": 100, "effort_note": "课后 1–3 h",
  "content_summary": "…",
  "schedule": { "scheduled_at": "2026-10-10T12:00:00Z", "meeting_link": "https://...", "status": "scheduled" },
  "preview_unlocked": true,
  "preview": { "intro": "…", "questions": ["…"], "keywords": ["…"] },
  "preview_read": false,
  "materials": [
    { "id": 1, "title": "《大规模语言模型》架构章", "mat_type": "book", "required": true, "url": "https://..." }
  ],
  "homework_def": "手画 Transformer block 图（含数据流与张量形状）+ 问题笔记",
  "homework_note": "V1 作业通过邮件提交，讲师在下次 1v1 面评中点评",
  "recorded_items": null
}
```
- 录播课时额外返回 `recorded_items`（同 part_group 逐讲：code/title/duration/video_url/done）与 `code_url`（代码包外链）
- `preview` 在未到 T-2 时返回 `null` + `preview_unlocked:false`（后端拦截，防越权读未解锁内容）

### POST /lessons/{code}/activity（行为标记）
```json
{ "act_type": "preview_read" }        // 或 "recorded_done"
// 200 { "ok": true }
```
- 幂等（UNIQUE 约束 + upsert）；只允许标记自己排期内的课时

### GET /links/magic/{token}（邮件直达落地）
- 邮件内链接格式：`{APP_BASE_URL}/l/{magic_link_token}`
- 落地页用 token 换取 JWT（7 天有效）并跳转目标页（`?to=/pages/lesson/index?code=T01`），实现「邮件一点直达、免登录」

## 4. 运营后台（/api/admin/*，staff token）

### POST /admin/login
```json
{ "email": "...", "password": "..." }
// 200 { "token": "<staff jwt>", "staff": { "name": "Rick" } }
```
- 首次登录（ADMIN_BOOTSTRAP_EMAIL 且密码为初始值）返回 `must_change_password: true`，强制走改密页

### GET /admin/students?cohort_id=1&page=1
```json
{
  "items": [
    {
      "id": 1, "name": "同学A", "email_masked": "y***@example.com", "cohort": "202610 期",
      "status": "active",
      "progress": { "one_on_one_done": 3, "preview_read_rate": 0.8, "recorded_done": 6 },
      "last_login_at": "2026-10-09T14:00:00Z"
    }
  ],
  "total": 3
}
```
- 筛选参数：`cohort_id`、`stale=1`（7 天未登录，掉队筛选）

### GET /admin/schedules?cohort_id=1&student_id=&lesson_code=
- 返回排期矩阵数据：学员 × 课时（分页或按学员分组，前端做表格）

### PUT /admin/schedules/{id}
```json
{ "scheduled_at": "2026-10-10T12:00:00Z", "meeting_link": "https://meeting.tencent.com/d/xxx", "status": "scheduled" }
// 200 { "ok": true, "email_triggered": "schedule_confirm" }
```
- 保存后自动触发：首次排期 → `schedule_confirm`；时间跨天变更 → `schedule_change`（原→新）
- 课时不排期时也可只改 status（如 done，手动结课）

### POST /admin/schedules/{id}/send-reminder
```json
{ "mail_type": "preview_reminder" }    // 或 class_reminder
// 200 { "ok": true, "queued": true }
```
- 前置校验：meeting_link 非空（否则 400 LINK_REQUIRED）
- 走统一发送服务（防重 + 重试，见 04 文档 6.4）

### POST /admin/students（导入白名单）
```json
{ "emails": ["a@x.com", "b@x.com"], "cohort_id": 1 }
// 200 { "imported": 2, "duplicated": 0 }
```

### GET /admin/email-logs?mail_type=&status=&page=
```json
{ "items": [ { "id": 9, "to_email_masked": "y***@example.com", "mail_type": "preview_reminder", "lesson_code": "T01", "status": "sent", "sent_at": "…", "retry_count": 0 } ], "total": 120 }
```
### POST /admin/email-logs/{id}/retry   → 失败一键重发

### GET /admin/preview/student-view（学员视图预览）
- 返回与 GET /map 相同结构（以指定 student_id 视角），运营核对上架内容用

## 5. 安全要点（实现 checklist）

- [ ] 密码 bcrypt（cost=12）；任何接口不回传 password_hash
- [ ] 登录失败计数按邮箱+IP，5 次锁 10 分钟，锁定提示走邮件
- [ ] verify/reset/magic_link token 一次性（used_at 判定）且过期拒绝
- [ ] resend-verification / forgot-password 对未注册邮箱返回相同成功文案
- [ ] 学员接口一律从 JWT 取 student_id，绝不信任 body/query 传入的 student_id
- [ ] 邮件内链接一律 HTTPS + `APP_BASE_URL` 前缀拼接（防 host 注入）
- [ ] admin 路由统一依赖 `scope=staff` 校验中间件
- [ ] SQLite 参数化查询（SQLAlchemy ORM 默认满足），无拼接 SQL
