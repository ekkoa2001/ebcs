# API 兼容策略与新接口清单

迁移期间现有页面继续调用下面的旧接口。新页面在对应阶段改调规范化接口。兼容层负责把旧 JSON 形状读出和写回新表，不要求这次就改前端。

## 1. 必须保持的旧接口

会话 Cookie 名保持 `sana_session`。写请求继续要求 `X-CSRF-Token`，并校验 `Origin`。

| 方法 | 路径 | 现行为 | 兼容要求 |
| --- | --- | --- | --- |
| GET | `/`、`/index.html`、`/admin` | 按登录状态返回页面 | 路径和页面不变 |
| GET | `/workshop.js`、`/workshop.css`、`/ui-fixes.css`、`/team-client.js`、`/gsap.min.js` | 返回静态文件 | 路径不变 |
| GET | `/media/{id}` | 从 BLOB 返回图片 | 继续按原 id 返回，文件化后也不改地址 |
| POST | `/api/login` | 登录并写 Cookie | 请求和 `{ok:true}` 不变 |
| POST | `/api/logout` | 清除会话 | 保持 |
| POST | `/api/password` | 校验旧密码并改密 | 保持 12 位规则和重新登录 |
| GET | `/api/session` | 用户、角色、CSRF、资料 | 字段名保持 |
| GET、POST | `/api/state` | 整包读取和保存 `entries` | 读出仍是旧记录形状；写入经兼容层拆到新表，再组装回旧形状 |
| POST | `/api/entries/patch` | 按条目前后对比保存，冲突返回 409 | 冲突语义、作者限制和广告限制保持 |
| GET | `/api/log` | 管理员查看操作记录 | 保持时间、操作者、动作 |
| GET | `/api/users` | 管理员账号列表 | 字段保持 |
| POST | `/api/users/create`、`/api/users/update` | 创建、角色、启停、重置密码 | 行为保持 |
| GET | `/api/presence` | 近两分钟在线人数 | 保持 |
| GET、POST | `/api/comments`、`/api/comments/all` | 按记录或全部评价 | 保持 |
| POST | `/api/comments/delete`、`/api/comments/like` | 删除和点赞 | 保持作者和管理员规则 |
| GET、POST | `/api/events`、`/api/events/read`、`/api/events/read-one` | 动态和已读 | 保持 |
| POST | `/api/profile`、`/api/team/update` | 个人资料、团队岗位 | 保持 |
| GET | `/api/archive` | 管理员归档列表 | 保持 |
| POST | `/api/archive/restore` | 管理员恢复 | 保持 |
| GET | `/api/team` | 管理员成员列表 | 保持 |

`/api/state` 和 `/api/entries/patch` 在验证通过前不能删除。最终业务页不再把它们当主数据源。

## 2. 新接口清单

新接口使用 `/api/v1`，Cookie 会话、CSRF 和 RBAC 与兼容层相同。列表统一支持搜索、筛选和分页。写操作返回版本号，冲突返回 409。

| 分组 | 路径 | 用途 |
| --- | --- | --- |
| auth | `/api/v1/auth/login`、`logout`、`session`、`password` | 新页面登录和会话 |
| users | `/api/v1/users`、`/api/v1/users/{id}` | 用户、资料、启停、重置密码 |
| creative | `/api/v1/hooks`、`/product-entries`、`/scripts`、`/scripts/{id}/shots`、`/scripts/{id}/videos` | 钩子、出场、脚本、分镜排序、成品 |
| content | `/api/v1/content-projects`、`/content-assets` | 品牌内容项目和图片 |
| marketing | `/api/v1/plans`、`/plans/{id}/stages`、`/lifecycle-plans`、`/lifecycle-nodes` | 方案、阶段、生命周期 |
| analytics | `/api/v1/campaigns`、`/period-records`、`/analytics/summary` | 投放批次、周期和后端汇总 |
| competitors | `/api/v1/competitor-insights` | 六类竞品洞察 |
| comments | `/api/v1/comments`、`/replies`、`/likes` | 通用评价 |
| notifications | `/api/v1/notifications` | 动态、未读和已读 |
| media | `/api/v1/media` | 上传、去重、预览和缩略图；旧 `/media/{id}` 另留 |
| admin | `/api/v1/admin/types`、`tags`、`archives`、`activity-logs`、`settings` | 类型、标签、归档、审计、设置 |

归档使用软删除。永久删除单独提供管理员接口，并要求二次确认。指标计算只在 analytics 服务端完成，缺失值不按 0 参与计算。
