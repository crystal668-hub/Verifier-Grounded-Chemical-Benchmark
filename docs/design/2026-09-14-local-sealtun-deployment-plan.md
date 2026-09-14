# VGB 题目审核系统：本机 + Sealtun 部署计划

日期：2026-09-14  
状态：待审核  
目标环境：macOS 本机、Docker Desktop、Sealtun HTTPS 隧道

## 1. 目标与边界

本方案将 VGB 题目审核系统长期运行在一台固定的 macOS 电脑上，通过
Sealtun 提供公网 HTTPS 入口。公网不直接开放应用端口，访问者先通过
Sealtun 的入口认证，再使用审核系统的个人账号登录。

本方案以低运维成本和可接受的偶发中断为目标，不承诺基础设施级高可用。
以下情况会造成预期内的服务中断：

- 本机关机、重启、休眠或用户未登录；
- Docker Desktop、审核系统容器或 Sealtun daemon 未启动；
- 本地断电、断网、路由器重启或运营商故障；
- Sealtun 区域或控制面不可用；
- 人工升级、备份恢复或故障处理期间暂停服务。

默认服务目标如下：

- 可用性：尽力保持持续在线，不设置正式 SLA；
- 恢复时间目标（RTO）：发现故障后 30 分钟内恢复；
- 恢复点目标（RPO）：最多丢失 24 小时内的审核数据；
- 用户规模：2–20 人；
- 部署实例：单实例；
- 数据库：SQLite；
- 公网入口：Sealtun 生成域名，稳定后可绑定自定义域名；
- 业务数据：只保存在本机持久化目录，并每日生成异地加密备份。

## 2. 最终架构

```text
公网用户浏览器
    |
    | HTTPS
    v
Sealtun 公网代理
    |  Basic Auth / 可选 IP 策略
    |
    | 加密隧道
    v
本机 Sealtun daemon
    |
    | 127.0.0.1:8000
    v
Docker Desktop
    |
    v
VGB review-system 容器
    |
    +-- /app/review_system/data/review.db
    +-- /app/review_system/data/attachments/
```

关键边界：

- Docker 端口只绑定 `127.0.0.1:8000`，局域网和公网不能直接访问；
- Sealtun 是唯一公网入口，不在路由器配置端口转发；
- 不需要 Caddy，公网 TLS 由 Sealtun 终止；
- Sealtun Basic Auth 只保护公网业务流量，不能替代应用账号权限；
- 正式题库仍以容器镜像中的 `src/verifier_grounded_benchmark` 为唯一可信来源；
- SQLite、批注、草稿和附件使用宿主机持久化目录，不写入容器层；
- 中栏不返回或展示附件正文，附件内容只通过右栏专用接口读取。

## 3. 当前状态与上线阻断项

截至本文档编写时：

- 本机已安装 Sealtun `0.0.16`；
- Sealtun 已登录 `https://gzg.sealos.run`；
- Sealtun daemon 正在运行；
- 当前审核服务由临时 Python 进程监听 `127.0.0.1:8000`；
- Docker Compose 尚未成功构建，最近一次失败原因为访问 Docker Hub 超时；
- 当前 Compose 将 `8000` 发布到所有主机接口；
- 当前应用允许默认管理员密码 `change-me-now`；
- 当前登录 Cookie 固定为 `secure=False`；
- 尚未实现登录限流、登录失败审计、会话集中撤销和健康检查；
- 数据库目前使用 Docker named volume，尚未形成可审计的宿主机备份路径。

下列事项为公网开放前的强制条件：

1. 删除前端预填的管理员用户名和密码。
2. 删除后端默认管理员密码；首次启动缺少管理员密码时必须拒绝启动。
3. 将生产 Cookie 配置为 `Secure`、`HttpOnly`、`SameSite=Lax`。
4. 提供密码修改、管理员重置密码、账号停用和会话撤销能力。
5. 对登录接口增加按来源 IP 和用户名的限流，并记录失败审计事件。
6. 增加无需登录且不泄露内部信息的 `/healthz` 接口。
7. Compose 端口改为 `127.0.0.1:8000:8000`。
8. 数据改用明确的宿主机目录并验证备份、恢复过程。
9. Dockerfile 使用 `npm ci` 和 lockfile，固定生产依赖及基础镜像版本。
10. 修复 Docker Hub 网络问题，并完成一次全新环境镜像构建。

上述条件未全部验收前，不创建面向协作者的长期公网隧道。

## 4. 仓库部署配置

### 4.1 生产环境文件

在 `review_system/` 下维护以下文件：

```text
review_system/
  compose.production.yml       # 可提交，不包含秘密
  sealtun.yaml                 # 可提交，只引用环境变量
  .env.production.example      # 可提交，只包含变量名和说明
  data/                        # 不提交，宿主机持久化数据
  backups/                     # 不提交，本地备份暂存
```

真实的 `.env.production` 不进入 Git，权限设置为仅当前用户可读：

```bash
chmod 600 review_system/.env.production
```

需要的变量：

```dotenv
REVIEW_ADMIN_USER=<初始开发者用户名>
REVIEW_ADMIN_PASSWORD=<至少 16 位随机密码>
REVIEW_SECRET_KEY=<至少 32 字节随机值>
REVIEW_COOKIE_SECURE=true
REVIEW_DATA_DIR=/app/review_system/data
```

管理员密码只用于初始化空数据库。初始化后通过应用内密码修改流程轮换，部署脚本
不得在日志中输出任何秘密。

### 4.2 生产 Compose 约束

生产 Compose 必须满足：

```yaml
services:
  review-system:
    image: vgb-review-system:<固定版本>
    restart: unless-stopped
    env_file:
      - .env.production
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ./data:/app/review_system/data
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
```

镜像在本仓库构建，包含经过验证的题库源码。生产部署不得挂载宿主机 `src/` 覆盖镜像，
避免运行版本和镜像版本不一致。

### 4.3 Sealtun 声明式配置

使用稳定名称管理隧道，不设置 TTL：

```yaml
version: v1
tunnels:
  - name: vgb-review
    localPort: 8000
    protocol: https
    basicAuth:
      username: vgb-review
      passwordEnv: SEALTUN_BASIC_AUTH_PASSWORD
    readyTimeout: 90s
```

`SEALTUN_BASIC_AUTH_PASSWORD` 不写入 YAML 或 Git。初始部署先使用 Sealtun 生成域名。
如后续绑定 `review.example.com`，在该 tunnel 中加入 `domain`，将域名 CNAME 指向
Sealtun 返回的 Sealos host，并在 DNS 生效后执行域名验证。

固定出口 IP 的团队可以增加 `ipAllowlist`。成员经常使用移动网络时不默认启用，避免正常
用户因 IP 变化被锁定在系统外。

## 5. 首次部署步骤

### 阶段 A：应用加固与验证

1. 在独立功能分支实现第 3 节列出的上线阻断项。
2. 运行后端测试、前端类型检查、前端构建和仓库相关回归测试。
3. 构建 wheel 和 sdist，确认 `review_system/`、数据库和附件没有进入公开发行包。
4. 使用空临时目录启动容器，验证必须提供管理员密码才能初始化。
5. 验证题库同步成功加载四个正式 track，不加载 calibration。
6. 验证包含 CIF/XYZ 的题目在中栏没有附件正文，右栏可以读取完整附件。
7. 为镜像设置不可变版本，例如 Git commit SHA，禁止生产环境依赖 `latest`。

验收标准：全部检查通过，镜像版本、源码 commit 和题库快照可以相互对应。

### 阶段 B：准备本机运行环境

1. 将本机接入稳定电源，建议同时为电脑、路由器和光猫配置 UPS。
2. macOS 在接通电源时禁止自动睡眠，允许显示器单独关闭。
3. 在 Docker Desktop 中启用登录后自动启动。
4. 确认磁盘至少预留 20 GB，并开启系统磁盘加密。
5. 将仓库放在固定路径，不从临时目录或网络盘运行。
6. 创建 `review_system/data/` 和 `review_system/backups/`，确认均被 Git 忽略。
7. 创建 `.env.production`，生成独立随机秘密并限制文件权限。
8. 停止当前临时 Uvicorn 进程，释放 `127.0.0.1:8000`。

验收命令：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
docker version
docker compose version
sealtun --version
sealtun status --json
```

阶段结束时，`8000` 应未被旧进程占用，Docker 和 Sealtun 均处于可用状态。

### 阶段 C：启动审核系统容器

```bash
cd /Users/xutao/verifier-grounded-benchmark/review_system
docker compose -f compose.production.yml build --pull
docker compose -f compose.production.yml up -d
docker compose -f compose.production.yml ps
docker compose -f compose.production.yml logs --tail 100 review-system
```

仅从本机验证：

```bash
curl --fail http://127.0.0.1:8000/healthz
curl --fail http://127.0.0.1:8000/
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

`lsof` 或 Docker 端口信息必须显示绑定 `127.0.0.1:8000`，不能显示
`*:8000` 或 `0.0.0.0:8000`。

### 阶段 D：创建 Sealtun 公网入口

在同一终端中安全注入网关密码：

```bash
export SEALTUN_BASIC_AUTH_PASSWORD='<从密码管理器读取>'
cd /Users/xutao/verifier-grounded-benchmark/review_system
sealtun apply -f sealtun.yaml --dry-run
sealtun diff -f sealtun.yaml
sealtun apply -f sealtun.yaml
unset SEALTUN_BASIC_AUTH_PASSWORD
```

不得使用包含明文密码的 `--basic-auth username:password`，避免秘密进入 shell history。

创建后执行：

```bash
sealtun list --check
sealtun inspect vgb-review --remote
sealtun logs vgb-review --tail 100
```

记录以下非秘密信息：

- tunnel ID：`vgb-review`；
- 生成的 HTTPS 地址；
- Sealtun region；
- 应用镜像版本；
- 源码 commit；
- 上线时间和操作人。

### 阶段 E：公网验收和账号交付

使用不连接本机 Wi-Fi 的手机蜂窝网络进行验收：

1. HTTPS 证书有效，无浏览器安全警告。
2. 未通过 Sealtun Basic Auth 时无法访问应用。
3. 通过网关后仍必须使用应用个人账号登录。
4. 开发者、协作者权限符合预期，停用账号无法登录。
5. 题目、评分、schema、讨论和草稿流程可用。
6. 中栏任何视图均不显示附件正文；附件只在右栏显示。
7. 退出登录后受保护 API 返回 `401`。
8. 直接访问本机局域网地址的 `8000` 端口失败。
9. `/healthz` 可被监控访问，但不泄露版本、路径、账号或数据库信息。
10. 日志不包含密码、Cookie、CSRF token 或附件正文。

验收完成后，为每位成员创建独立协作者账号，通过独立安全渠道分别发送：

- 公网 HTTPS 地址；
- Sealtun 网关用户名和密码；
- 审核系统个人用户名和初始密码；
- 首次登录修改密码要求；
- 可预期的维护窗口和故障反馈方式。

不得共享开发者账号或在同一消息中发送两层认证的全部凭据。

## 6. 开机恢复与日常运行

本方案依赖 macOS 用户会话中的 Docker Desktop。电脑重启后需要完成用户登录，之后依次确认：

```bash
docker compose -f /Users/xutao/verifier-grounded-benchmark/review_system/compose.production.yml ps
curl --fail http://127.0.0.1:8000/healthz
sealtun status --json
sealtun list --check
```

Compose 的 `restart: unless-stopped` 负责恢复应用容器。Sealtun daemon 负责维持已创建的 daemon
隧道；如果 session 未恢复，执行：

```bash
sealtun resume vgb-review
```

不得通过 macOS 自动登录换取无人值守恢复，因为它会降低本机账号安全。计划内系统重启应安排
管理员在场登录并完成上述检查。

日常每周检查：

```bash
docker compose -f review_system/compose.production.yml ps
docker compose -f review_system/compose.production.yml logs --tail 100 review-system
sealtun list --check
sealtun metrics vgb-review
```

配置一个位于本机网络之外的 HTTPS 可用性监控，每 5 分钟访问一次入口，连续 3 次失败后通知
管理员。监控账号只用于健康检查，不使用开发者账号。

## 7. 数据备份与恢复

### 7.1 备份策略

每日执行一次一致性备份：

1. 调用应用维护模式或 SQLite backup API 生成一致的数据库副本；不得在有写入时直接复制
   `review.db`。
2. 将数据库副本和附件目录打包。
3. 使用独立密钥加密备份。
4. 上传到不依赖本机磁盘的对象存储或另一台设备。
5. 校验压缩包和 SHA-256 摘要。
6. 本地保留 7 天，异地保留 30 天。

备份不得包含 `.env.production`、Sealtun 凭据、会话 Cookie 或明文密码。应用数据库中的活跃
会话属于敏感数据，备份存储必须加密且限制访问。

### 7.2 恢复流程

1. 暂停公网入口：`sealtun stop vgb-review`。
2. 停止应用容器。
3. 将当前损坏数据目录复制到隔离位置用于调查，不直接覆盖。
4. 校验待恢复备份的摘要并解密。
5. 恢复数据库和附件到新的空目录。
6. 启动容器并执行 schema 迁移和完整性检查。
7. 验证登录、题库、批注、草稿和附件。
8. 恢复隧道：`sealtun start vgb-review`。
9. 从外部网络执行一次完整验收。

每季度至少在临时目录完成一次恢复演练。只有实际恢复成功的备份才视为有效备份。

## 8. 更新与回滚

每次更新遵循以下顺序：

1. 公告短暂维护窗口。
2. 确认 Git 工作区干净并记录当前 commit、镜像版本和题库快照指纹。
3. 创建并验证更新前备份。
4. 拉取或切换到经过审核的 release tag。
5. 在新镜像上运行测试和前端生产构建。
6. 构建带 commit SHA 的新镜像。
7. 停止 Sealtun 公网入口或开启应用维护模式。
8. 执行数据库迁移并启动新容器。
9. 本机健康检查通过后恢复隧道。
10. 从外部网络执行核心流程验收。

回滚条件：健康检查失败、数据库迁移失败、登录失败、题库同步异常或附件边界被破坏。

回滚时使用更新前镜像和备份，不通过 Git reset 或覆盖工作区恢复。涉及不可逆数据库迁移时，
必须恢复更新前数据库副本。回滚后记录原因并暂停再次发布。

## 9. 故障处理手册

### 应用页面不可访问

```bash
curl --fail http://127.0.0.1:8000/healthz
docker compose -f review_system/compose.production.yml ps
docker compose -f review_system/compose.production.yml logs --tail 200 review-system
```

如果本机健康检查失败，先恢复容器，不要先重建隧道。

### 本机可访问但公网不可访问

```bash
sealtun status --json
sealtun list --check
sealtun inspect vgb-review --remote
sealtun logs vgb-review --tail 200
sealtun doctor --json
```

确认应用正常后，可执行 `sealtun resume vgb-review`。不要创建同名之外的临时隧道绕过既有
入口策略，以免产生未受管理的公网地址。

### 本地断网或断电

恢复电源和网络后登录 macOS，确认 Docker Desktop、容器、Sealtun daemon 和 tunnel 依次恢复。
公网监控恢复正常后再宣布服务可用。

### 凭据疑似泄露

1. 立即停止 tunnel。
2. 轮换 Sealtun Basic Auth 密码并重新应用声明式配置。
3. 停用相关应用账号并撤销其全部会话。
4. 检查登录和审核事件日志。
5. 确认无异常修改后恢复 tunnel。

### SQLite 或附件损坏

停止公网入口和应用，保留故障副本，按第 7.2 节恢复最近的有效备份。不得在原数据库上反复
尝试破坏性修复。

## 10. 安全基线

- Sealtun 网关密码和应用密码必须不同；
- 每位用户使用独立账号，开发者权限按最小需要授予；
- 网关和应用密码存入密码管理器，不写入仓库、脚本或聊天记录；
- 登录失败限流，连续异常登录触发告警；
- Cookie 仅通过 HTTPS 发送，并保持 `HttpOnly`；
- 不公开 `8000`、数据库文件、附件目录、Docker socket 或 Sealtun 控制目录；
- macOS 启用 FileVault、自动安全更新和屏幕锁定；
- Docker Desktop、基础镜像、Python、Node 和 Sealtun 定期升级；
- 上传文件限制为批准的文本、PNG/JPEG 和 PDF 类型，最大 20 MiB；
- PDF 和图片只以内联安全预览或下载方式提供，不执行主动内容；
- 日志和备份按敏感数据管理；
- 离职或不再参与审核的账号立即停用并撤销会话。

## 11. 最终验收清单

- [ ] 所有上线阻断项均已实现并通过测试；
- [ ] 生产镜像可从空环境重复构建；
- [ ] 容器仅绑定 `127.0.0.1:8000`；
- [ ] Compose、Docker Desktop 和 Sealtun daemon 能在计划内重启后恢复；
- [ ] Sealtun 配置经过 `dry-run`、`diff` 和真实 `apply`；
- [ ] 公网 HTTPS、Basic Auth 和应用登录全部有效；
- [ ] 所有协作者使用独立账号；
- [ ] 中栏从 API 到 UI 均不包含附件正文；
- [ ] 外部监控可以发现应用或 tunnel 中断；
- [ ] 每日异地加密备份已运行；
- [ ] 备份恢复演练成功；
- [ ] 更新和回滚流程至少演练一次；
- [ ] 运维人员持有必要账号、密码管理器条目和故障处理文档。

## 12. 决策结论

本机 + Sealtun 能满足小团队公网协作和低成本部署要求，但可用性上限由本机电源、网络、用户
登录状态和 Docker Desktop 决定。方案接受这些中断，不把 Sealtun 视为应用托管平台。

只有完成第 3 节的公网加固、建立异地备份并通过第 11 节验收后，才应向协作者发布公网地址。
如果未来需要无人值守重启、明确 SLA、多实例或本地设备故障后自动接管，应迁移到云主机或托管
容器平台，而不是继续增加本机部署复杂度。
