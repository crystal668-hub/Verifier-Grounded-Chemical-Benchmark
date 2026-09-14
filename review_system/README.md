# VGB 题目审核系统

独立的 FastAPI + React 审核工作台。正式题库只从仓库 `src/verifier_grounded_benchmark` 读取；SQLite 仅保存快照、批注、草稿和附件。

本地开发使用 `docker compose up --build`。公网生产部署必须使用
[`compose.production.yml`](compose.production.yml)，不得使用开发 Compose 中的默认配置。

```bash
cd review_system
./scripts/generate-secrets.sh
docker compose -f compose.production.yml up --build -d
set -a && . ./.env.sealtun && set +a
sealtun apply -f sealtun.yaml --dry-run
sealtun diff -f sealtun.yaml
sealtun apply -f sealtun.yaml
unset SEALTUN_BASIC_AUTH_PASSWORD
```

生产容器只绑定 `127.0.0.1:8000`，公网访问只允许经过 Sealtun HTTPS 和 Basic Auth。
附件正文只在右侧附件栏展示；中栏只显示附件元信息和跳转入口。完整部署、恢复和故障处理见
[`../docs/design/2026-09-14-local-sealtun-deployment-plan.md`](../docs/design/2026-09-14-local-sealtun-deployment-plan.md)。
