# 部署文档 · NiceOffer 交付系统 V1

> 依据：01 文档第 5 节部署方案 + 实际实现。覆盖本地开发、演示部署、生产部署、备份、上线冒烟全流程。
> 代码结构：`server/`（FastAPI 后端）+ `student-h5/`（uni-app 学员端）+ `admin-web/`（运营后台）。

---

## 1. 架构与端口

```
                      https://learn.<域名>
                              │ Caddy（自动 HTTPS，反代 + 静态）
        ┌─────────────────────┼──────────────────────┐
        │ /                →  student-h5 构建产物（静态）│
        │ /admin/          →  admin-web 构建产物（静态）│
        │ /api/            →  uvicorn 127.0.0.1:8000  │
        └─────────────────────┴──────────────────────┘
                              │
                     FastAPI 单进程（API + APScheduler）
                     SQLite WAL（server/data/app.db）
                     SMTP（腾讯企业邮箱，唯一通知通道）
```

- **单进程**：APScheduler（T-2 / T-0 / 失败重发 / 自动结课）随后端进程跑，无需独立部署。
- **同域**：两个前端与 API 同域（`learn.<域名>`），前端请求相对路径 `/api`，无 CORS 问题。
- **演示模式例外**：本地演示可不用 Caddy，由 FastAPI 单端口直接托管全部内容（见第 3 节）。

## 2. 环境变量（server/.env）

复制 `server/.env.example` 为 `.env`，按环境修改：

| 变量 | 说明 | 生产值 |
|---|---|---|
| `DATABASE_URL` | SQLite 路径 | `sqlite:///./data/app.db`（默认，不用改） |
| `JWT_SECRET_STUDENT` / `JWT_SECRET_STAFF` | 双 token 签名 secret | **生产必须重新生成**：`python -c "import secrets;print(secrets.token_hex(32))"` 各一个 |
| `JWT_EXPIRE_DAYS` | token 有效期 | 14 |
| `EMAIL_BACKEND` | 邮件后端：`console` / `mailpit` / `smtp` | `smtp` |
| `SMTP_HOST` / `SMTP_PORT` | 腾讯企业邮箱 | `smtp.exmail.qq.com` / `465` |
| `SMTP_USER` / `SMTP_PASS` | 发件账号 + SMTP 授权码 | Rick 提供 |
| `SMTP_SSL` | 465 端口自动 SSL | `true` |
| `MAIL_FROM_NAME` | 发件人显示名 | `NiceOffer 班主任` |
| `APP_BASE_URL` | 邮件内链接前缀 | `https://learn.<域名>` |
| `ADMIN_BOOTSTRAP_EMAIL` / `ADMIN_BOOTSTRAP_PASSWORD` | 初始运营账号（首登强制改密） | Rick 邮箱 + 初始密码 |
| `TZ` | 定时任务时区 | `Asia/Shanghai` |

**纪律（05 文档 §1）**：secret 只进 `.env`（已 gitignore），代码/注释/commit/日志禁止出现真实密钥。

## 3. 本地开发与演示部署

### 3.1 后端

```bash
cd server
pip install -r requirements.txt
cp .env.example .env            # 本地默认值即可用（EMAIL_BACKEND=console）
python -m uvicorn app.main:app --reload --port 8000
```

- 首次启动自动：建表（SQLite WAL）→ 幂等种子（5 模块 / 42 课时卡 / 25 资料 / 202610 期 / 初始运营账号）→ 启动定时任务。
- API 调试台：http://localhost:8000/docs
- 测试：`python -m pytest`（43 条，独立内存库，不碰 data/app.db）

### 3.2 前端开发模式（热更新）

```bash
# 学员端（vite dev server 5173，proxy /api → 8000）
cd student-h5 && npm install && npm run dev:h5

# 运营后台（vite dev server 5174，base /admin/，proxy /api → 8000）
cd admin-web && npm install && npm run dev
```

### 3.3 单端口演示部署（无 Caddy，推荐用于演示/验收前联调）

```bash
# 构建前端产物
cd student-h5 && npm run build:h5     # → student-h5/dist/build/h5
cd ../admin-web && npm run build      # → admin-web/dist

# FastAPI 直接托管：/api + /admin/ + /（见 server/app/main.py 静态托管段）
cd ../server && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问：

| 入口 | URL |
|---|---|
| 学员端 H5 | `http://<host>:8000/` |
| 运营后台 | `http://<host>:8000/admin/` |
| API 文档 | `http://<host>:8000/docs` |

邮件走 `console` 后端时，正文打印在 uvicorn 日志（含 verify / magic_link 等可点链接）。

### 3.4 邮件本地调试（mailpit）

```bash
docker run -d -p 1025:1025 -p 8025:8025 axllent/mailpit
# .env: EMAIL_BACKEND=mailpit（SMTP_HOST=localhost SMTP_PORT=1025）
# 收件箱 UI：http://localhost:8025 —— 可看六类邮件渲染、点 magic_link 直达
```

## 4. 生产部署（境外 VPS，备案期间）

**前置**：域名一台（DNS 解析到 VPS IP）、SMTP 授权码到位。服务器 Debian/Ubuntu 2C2G。

### 4.1 装机

```bash
sudo apt update && sudo apt install -y python3 python3-pip caddy
# Node 仅构建期需要；也可本地构建后只上传 dist（推荐，服务器免装 Node）
```

### 4.2 部署代码

```bash
git clone <本仓库> /opt/niceoffer && cd /opt/niceoffer

# 前端产物：本地构建后上传，或服务器构建
cd student-h5 && npm install && npm run build:h5
cd ../admin-web && npm install && npm run build

# 后端依赖 + 生产 .env（secret 重新生成！见第 2 节）
cd ../server
pip install -r requirements.txt
cp .env.example .env && vim .env    # EMAIL_BACKEND=smtp + 真实 SMTP/域名/账号

# 迁移（首次部署；此后每次拉代码如有新迁移重跑）
python -m alembic upgrade head
```

### 4.3 systemd 常驻

`/etc/systemd/system/niceoffer.service`：

```ini
[Unit]
Description=NiceOffer delivery API
After=network.target

[Service]
WorkingDirectory=/opt/niceoffer/server
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
Environment=TZ=Asia/Shanghai

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now niceoffer
curl http://127.0.0.1:8000/api/health   # {"ok":true}
```

### 4.4 Caddy 反代（自动 HTTPS）

`/etc/caddy/Caddyfile`：

```caddy
learn.<域名> {
    # 学员端 H5（uni-app hash 路由，单 index.html）
    handle {
        root * /opt/niceoffer/student-h5/dist/build/h5
        try_files {path} /index.html
        file_server
    }

    # 运营后台（SPA history 路由）
    handle /admin/* {
        uri strip_prefix /admin
        root * /opt/niceoffer/admin-web/dist
        try_files {path} /index.html
        file_server
    }

    # API
    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }
}
```

```bash
sudo systemctl reload caddy
# 验证：https://learn.<域名>/ 、/admin/ 、/api/health
```

> admin-web 构建时 `base: '/admin/'`，资源路径已带前缀；Caddy 侧 strip_prefix 与之匹配。

### 4.5 数据备份

```bash
# crontab -e（每日 03:00 备份，保留 30 份，可再同步到对象存储/另一台机）
0 3 * * * sqlite3 /opt/niceoffer/server/data/app.db ".backup '/opt/niceoffer/server/data/backup-$(date +\%F).db'" && find /opt/niceoffer/server/data -name 'backup-*.db' -mtime +30 -delete
```

### 4.6 备案完成后迁境内（01 文档 §5）

1. 新购境内服务器，同版本代码部署（重复 4.1–4.4）。
2. `APP_BASE_URL` 不变（域名不变），DNS 解析切境内 IP。
3. 停写 5 分钟 + 最终一次 `.backup`，拷贝 `data/app.db` 到新机。
4. 学员无感；随后启动 V1.5 小程序编译（学员端已通过 `build:mp-weixin` 零改动编译验证）。

## 5. 上线冒烟清单（05 文档 §4.3，切真实 SMTP 当天必做）

1. 运营后台导入白名单 → 用 **QQ / 163 / Gmail 三个真实邮箱**各注册一个测试账号。
2. 验证 verify 邮件 60 秒内到达且不进垃圾箱（进了→腾讯企业邮箱后台配 SPF/DKIM）。
3. 邮件内链接 HTTPS 可点、magic_link 免登录直达正确页面。
4. 后台邮件中心三条记录均 `sent`。
5. 后台排期一节课 → 1 分钟内学员端可见 + schedule_confirm 邮件到达。
6. 跑一遍 PRD 表 10-2 八条路径（375px 真机）。

## 6. 运维速查

| 场景 | 操作 |
|---|---|
| 看服务日志 | `journalctl -u niceoffer -f` |
| 重启 | `sudo systemctl restart niceoffer` |
| 更新代码 | `git pull && cd server && python -m alembic upgrade head && sudo systemctl restart niceoffer`（前端改动需重新 build） |
| 重置运营密码 | 改 `server/.env` 的 `ADMIN_BOOTSTRAP_*` 后删除 staff_user 表对应行重启（或直接 sqlite 改 password_hash，bcrypt cost=12） |
| 手动触发定时任务 | Python 内直接调用纯函数：`from app.services.scheduler import run_t2_reminders`（传 db + now） |
| 数据库位置 | `server/data/app.db`（WAL 模式，三个文件：app.db / -wal / -shm） |
