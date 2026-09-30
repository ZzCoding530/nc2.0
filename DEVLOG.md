# DEVLOG · V1 交付系统开发日志

## ⏳ 等待清单（Rick 每天看这节）
| 提出日 | 等什么 | 用在哪 | 阻塞吗 |
|---|---|---|---|
| 10-01 | 《课时安排定版 v3》逐课时明细原文 | 种子数据内容（当前 42 张课时卡按 02/03/04 文档结构与示例构造，见决策 #4） | 否，不影响开发与测试，拿到后替换 lessons_seed.json 重跑 seed 即可 |
| 10-01 | SMTP 授权码（腾讯企业邮箱） | 上线验收（4.3 送达冒烟） | 否，D10 前到位即可 |
| 10-01 | 域名 + DNS 权限 | 部署 | 否，D10 前到位即可 |

## 任务板（完成打勾）
- [x] D1–2 仓库骨架 + 建表（12 张表 + alembic 初始迁移）+ 42 张课时卡种子
- [x] D3 auth 全链路：注册→验证邮件→激活→登录→JWT（双 secret）→忘记/重置→magic_link
- [x] D4 学员端三 tab 框架 + 课程地图页（uni-app，H5 与 mp-weixin 双编译通过）
- [x] D5 课时详情页（预习/资料/作业三区）+ 行为标记（幂等）
- [x] D6 学习台（overview 聚合接口）
- [x] D7 运营后台：排期 CRUD（upsert + PUT）+ 学员列表（进度/掉队筛选/白名单导入）
- [x] D8 六类邮件模板 + 排期触发（confirm/change）+ 手动兜底发送
- [x] D9 APScheduler 定时任务（T-2 / T-0 / 失败重发 / 自动结课）+ 防重 + 重试
- [x] D10 代码侧完成：`pytest -q` 43 条全绿（覆盖 05 文档 3.2 全部 18 条必测用例）；uvicorn 真实启动冒烟通过（白名单导入→注册→激活→排期→schedule_confirm→学员端接口）
- [ ] 表 10-2 八条路径真机 walkthrough（需手机 375px 人工执行，代码路径均已就绪）
- [ ] 上线：切真实 SMTP + 域名 + Caddy 部署 + 送达冒烟（等等待清单 2/3 项）

## 验收记录
| 日期 | 路径/用例 | 结果 | 问题（级别） | 修复 commit | 复验 |
|---|---|---|---|---|---|
| 10-01 | 05 文档 3.2 #1–#18（18 条必测，pytest 43 条） | 全绿 | 无 | — | — |
| 10-01 | uvicorn 冒烟：/docs + 注册→激活→排期→overview/lesson 接口 | 通过 | 无 | — | — |
| 10-01 | student-h5 `build:h5` + `build:mp-weixin` | 通过 | 无 | — | — |
| 10-01 | admin-web `npm run build`（vue-tsc + vite） | 通过 | 无 | — | — |

## 决策记录（偏离文档时必写）
| 日期 | 决策 | 原因 |
|---|---|---|
| 10-01 | `email_log` 增加 `body` 列（02 DDL 未含） | 失败重发（后台按钮 + 每小时定时）需要原文；只加列不改列，兼容文档结构 |
| 10-01 | 密码哈希直接用 `bcrypt` 库，不用 `passlib` | passlib 1.7.4 依赖 Python 3.13 起移除的 `crypt` 模块，无法在 Python 3.14 运行；bcrypt cost=12 语义不变 |
| 10-01 | `ADMIN_BOOTSTRAP_EMAIL` 默认 `admin@example.com`（05 附录 B 写 `dev@local.test`） | email-validator 拒绝 `.test` 保留域名；同时满足「测试只用 @example.com 域」纪律 |
| 10-01 | 种子 42 张课时卡内容按文档线索构造 | 定版 v3 原文未入库；模块结构（M1–M4+FLEX）、代码（C×4/T×3/E×5/D×27/V×3=42）、T01 preview 等均按 02–04 文档示例；结构与数量与口径表完全一致（1v1 15 / 录播 27） |
| 10-01 | 新增接口：`POST /admin/schedules`（upsert）、`POST /admin/students/{id}/send-welcome`、`POST /admin/change-password`、`GET /admin/cohorts`、`GET /admin/lesson-cards`、`GET /schedules/{id}/calendar.ics` | 03 文档错误码表提到 upsert 但未定义创建接口；welcome 邮件标注「运营触发」但未给触发入口；首登改密 / 排期矩阵数据源 / 邮件内「加入日历」链接同理。字段风格与文档一致 |
| 10-01 | 录播课 display_status：`recorded_done` → done，无排期默认 pending | map 页录播组「已看 n/总讲数」依赖逐讲完成态；02 §4 五态规则未覆盖录播，此为口径补全 |
| 10-01 | 登录失败锁定为进程内存 dict（不落库） | V1 单进程部署，学员 ≤50；锁定期可走忘记密码（reset 后锁清除） |
| 10-01 | 定时任务遇到 meeting_link 为空的排期跳过（不报错），手动发送才 400 LINK_REQUIRED | 批量任务不应因单条脏数据中断；与 04 §6.8 一致 |
| 10-01 | admin「学员视图预览」iframe 为降级实现（学员端无 staff 视角登录态） | 上架核对以 `GET /admin/preview/student-view` 返回的 map JSON 为准；iframe 仅外观参考 |
| 10-01 | 邮件内链接用 H5 hash 路由 `{APP_BASE_URL}/#/pages/...` | uni-app H5 默认 hash 路由；切正式域名无需改动 |

## 日志
### 10-01
- 完成：全量开发（对照 01–05 文档）。后端 FastAPI（auth / 学员 / admin 三组路由 + EmailSender 抽象 + APScheduler + 幂等种子）；学员端 uni-app 9 页面（含 reset 落地页）；运营后台 Vue3+Element Plus 5 页面；alembic 初始迁移；测试 43 条全绿。
- 问题/决策：见决策记录表（10 条）。测试期发现的 bug 均已修复：register 错误码判定顺序（EMAIL_TAKEN 优先）、magic_link token 属性访问、map payload 缺 part_group、录播 display_status 口径。
- 明日/待办：表 10-2 八条路径真机 walkthrough；等 SMTP 授权码与 DNS 后做部署与送达冒烟。
