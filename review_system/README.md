# VGB 题目审核系统

独立的 FastAPI + React 审核工作台。正式题库只从仓库 `src/verifier_grounded_benchmark` 读取；SQLite 仅保存快照、批注、草稿和附件。

本地开发先设置 `REVIEW_ADMIN_PASSWORD`，再使用 `docker compose up --build`。公网生产部署必须使用
[`compose.production.yml`](compose.production.yml)，不得使用开发 Compose 中的默认配置。

```bash
cd review_system
./scripts/generate-secrets.sh
set -a && . ./.env.production && set +a
docker compose -f compose.production.yml up --build -d
set -a && . ./.env.sealtun && set +a
sealtun apply -f sealtun.yaml --dry-run
sealtun diff -f sealtun.yaml
sealtun apply -f sealtun.yaml
unset SEALTUN_BASIC_AUTH_PASSWORD
unset REVIEW_ADMIN_PASSWORD REVIEW_SECRET_KEY
```

生产容器只绑定 `127.0.0.1:8000`，公网访问只允许经过 Sealtun HTTPS 和 Basic Auth。
附件正文只在右侧附件栏展示；中栏只显示附件元信息和跳转入口。完整部署、恢复和故障处理见
[`../docs/design/2026-09-14-local-sealtun-deployment-plan.md`](../docs/design/2026-09-14-local-sealtun-deployment-plan.md)。

登录页支持自助注册。注册账号默认创建为启用的 `collaborator`，注册成功后会直接建立登录会话；只有已有开发者才能通过用户管理接口创建开发者账号。

在宿主机创建协作者账号时，使用环境变量传递初始密码，避免进入 shell history：

```bash
export REVIEW_NEW_USER_PASSWORD='<从密码管理器读取>'
docker compose -f compose.production.yml exec -T \
  -e REVIEW_NEW_USER_PASSWORD="$REVIEW_NEW_USER_PASSWORD" review-system \
  python -m review_system.manage create-user reviewer --role collaborator \
  --password-env REVIEW_NEW_USER_PASSWORD
unset REVIEW_NEW_USER_PASSWORD
```

## 标准发布流程

使用 `scripts/pipeline.sh` 固化测试、镜像构建、部署和验收。默认镜像标签为当前 commit 的短 SHA；生产发布必须显式传入版本或 SHA：

```bash
./scripts/pipeline.sh test
./scripts/pipeline.sh release --tag 2026.09.14-<commit>
./scripts/pipeline.sh verify
```

发布脚本要求工作区干净、存在 `.env.production`，先执行加密备份，再构建并启动版本化镜像，最后检查健康接口和回环端口。失败时不会继续后续阶段；回滚使用 `REVIEW_ROLLBACK_TAG=<previous-tag> ./scripts/pipeline.sh rollback`。Sealtun 的 `dry-run`、`diff`、`apply` 仍由管理员在本机验证通过后显式执行。
