# 创意钩子迁移

完成日期：2026-11-12

## 正式数据源

`creative_hooks` 已作为创意钩子的规范化数据表，支持 SQLite 与 PostgreSQL。

## 新接口

- `GET /api/v1/creative/hooks`
- `GET /api/v1/creative/hooks/{id}`
- `POST /api/v1/creative/hooks`
- `PUT /api/v1/creative/hooks/{id}`
- `DELETE /api/v1/creative/hooks/{id}`
- `POST /api/v1/creative/hooks/{id}/restore`

## 迁移与兼容

- 启动时从旧 `state.entries` 导入缺失的创意钩子。
- 老 UI 保存整组数据后，同步更新规范化钩子表。
- 新 API 写入后，同步更新老 UI 当前读取的兼容状态。
- 过渡期保持双向一致；产品出场和完整脚本完成迁移后，再移除整组状态兼容层。
- 已完成数量与 ID 对账：正式库 5 条，旧状态 5 条。

## 权限与数据安全

- 所有读操作要求 `content.read`。
- 新建要求 `content.create` 和 CSRF。
- 操作者只能修改自己的钩子。
- 管理员可修改全部钩子。
- 归档和恢复使用独立权限。
- 更新使用版本号进行乐观锁检查。
- 新建、修改、归档和恢复写入结构化审计日志。

## UI 影响

无视觉和布局变化。原有卡片、筛选、详情和编辑弹窗继续使用。

## 自动测试

- 旧钩子导入规范化表
- 新 API 新建并同步老 UI 状态
- 更新与版本冲突
- 归档与恢复
- 老 UI 保存后同步新表
- 测试数据库与生产 PostgreSQL 隔离

完整测试结果：`16 passed`
