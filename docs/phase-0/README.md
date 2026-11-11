# 阶段 0 准备产出

本目录是 README 第 24 节的准备结果。业务代码、页面和文件拆分都还没有开始。

Git 基线：`b15e69b`，提交说明为 `Establish the unmodified V1 baseline before the in-place upgrade.`

| 产出 | 位置 |
| --- | --- |
| 审计与功能清单 | [00-audit.md](00-audit.md) |
| 目标 ER 图 | [01-er.md](01-er.md) |
| 旧数据迁移映射 | [02-migration-map.md](02-migration-map.md) |
| API 兼容策略 | [03-api-compatibility.md](03-api-compatibility.md) |
| 权限矩阵 | [04-permission-matrix.md](04-permission-matrix.md) |
| 分阶段计划与阶段 0 验收 | [05-phase-plan.md](05-phase-plan.md) |
| 视觉基线 | [screenshots](screenshots) |
| 像素对比 | `tests/visual`，执行 `npx playwright test` |

数据库备份：`data/backups/Ekko-Script-Web-20261111-172532-049199.sqlite3`

`web`、`server`、`docs` 源码备份：`data/backups/phase0-source-20261111-172532.zip`。该压缩包生成于基线提交之后，不包含本目录。
