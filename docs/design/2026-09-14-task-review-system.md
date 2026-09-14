# VGB 题目审核系统

`review_system/` 是不进入 benchmark 发行包的独立 FastAPI + React 审核工作台。正式题目由部署版本的 `src/verifier_grounded_benchmark` 加载并生成带 commit 与内容指纹的 SQLite 快照；数据库只保存快照索引、账号、批注、草稿及附件。

界面使用目录、题目主面板、附件栏三栏布局。中栏只展示题干、规则、schema 元数据和题目级讨论；附件正文、图片或 PDF 预览只允许在右栏附件查看器中呈现。CIF/XYZ 等长输入通过展示层引用拆分，不改变源码内容。

开发者通过 `POST /api/v1/source-sync` 显式同步源码，草稿审批后由 `GET /api/v1/drafts/{id}/export` 导出 ZIP，开发者再通过 Git 合入并重新部署。默认适合小团队单机部署。开发、构建和部署统一通过 `review_system/scripts/pipeline.sh` 执行；生产镜像使用 commit/version 标签，Sealtun 更新仍需显式执行。
