# VGB 题目审核系统

独立的 FastAPI + React 审核工作台。正式题库只从仓库 `src/verifier_grounded_benchmark` 读取；SQLite 仅保存快照、批注、草稿和附件。

```bash
cd review_system
docker compose up --build
```

打开 http://localhost:8000。默认开发者账号为 `admin`，请通过 `REVIEW_ADMIN_PASSWORD` 修改密码。附件正文只在右侧附件栏展示；中栏只显示附件元信息和跳转入口。

备份：停止服务后复制 `data/review.db` 及附件目录。源码更新后，开发者调用 `POST /api/v1/source-sync` 显式同步。
