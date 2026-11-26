# Orca NAS

基于官方独立 Linux Server 的 Docker 部署项目；不修改上游，不运行 Electron 桌面。固定上游版本、镜像基础摘要和包校验和。当前仅支持 Linux x86_64。

## 安装与目录

NAS 目录 `/volume1/docker/orca`，本地源码项目 `orca-nas`。先按 `.env.example` 创建 `.env`，将 `BIND_IP`、`ORCA_PAIRING_ADDRESS` 设置为 NAS 内网或 Tailscale 地址。准备目录：

```sh
mkdir -p data/home data/profile data/agents workspace .cache
chown -R 1026:100 data workspace
chmod 700 data
```

官方发行包放入 `.cache/orca-server-linux-x64.tar.gz`，Docker 构建自动校验。运行：

```sh
docker compose build
docker compose up -d
```

| 宿主目录 | 容器目录 | 保存内容 |
| --- | --- | --- |
| `workspace` | `/workspace` | Git 项目、未提交文件和工作树；项目应始终使用此路径 |
| `data/profile` | `/data/profile` | 项目登记、Orca 配置、会话及配对信息 |
| `data/home` | `/data/home` | Agent 认证、SSH 密钥、Git 配置、GitHub CLI 登录 |
| `data/agents` | `/data/agents` | 独立安装的 Agent CLI 及版本记录 |

重建容器不删除以上目录。不要使用 `docker compose down -v` 作为重置方法，也不要清理 `data`。Orca 内置数据库不直接改成 PG。

## Agent 与 Git

镜像含 git、gh、OpenSSH、Python、tmux、ripgrep。内置 Node 22 支持 npm CLI；Orca 使用官方包自带 Node。Agent 程序、账号授权与 Orca 版本独立维护。

```sh
# VERSION 必须填写已核对的具体版本号，不用 latest。
docker compose exec orca orca-agent codex VERSION
docker compose exec orca orca-agent claude VERSION
# 首次按官方交互完成授权，不能自动沿用电脑端授权。
docker compose exec orca orca account add --agent codex
docker compose exec orca orca account add --agent claude
docker compose exec orca orca account list
# GitHub 使用官方交互式授权；保存到持久化 HOME。
docker compose exec orca gh auth login
```

SSH 密钥使用 `/data/home/.ssh`，权限目录 700、私钥 600；首次核对服务器指纹。不挂载 NAS 管理员整份 HOME，不注入其他服务的 Token。后续其他 CLI 可进入容器安装到 `/data/agents`，但须逐个验证上游兼容性；没有宣称所有 Agent 均已接入。

## 访问

官方远程模式仍为 Beta。只通过内网、Tailscale 或可信认证隧道访问；不转发公网端口。默认 Compose 未填写 `.env` 时仅监听回环地址。启动不向日志打印配对凭据。桌面客户端与移动客户端需使用 Orca 的配对授权，NAS 上的 CLI 认证不等于客户端配对。使用 `docker compose exec orca orca pair --address NAS内网IP` 生成桌面配对链接；移动网页使用 `docker compose exec orca orca pair --mobile --address NAS内网IP`。配对链接只在可信终端展示，不贴入日志。完整桌面 IDE 与服务器包里的 mobile-web 界面能力不同。

容器不授予 privileged，不挂载 Docker socket，不挂载 NAS 根目录。Agent 可读写挂载的项目与自身凭据，运行任意项目命令前应审阅权限。限制总内存 3 GiB、进程数 512；Agent 并发应从 1 开始。ASVS 13.1.1/13.3.2：认证文件不进入源码或镜像，备份也按凭据文件管理。

## 更新与回退

先核对官方 Release 的 Server 版本、SHA256 和协议兼容性。升级客户端和服务器时保持兼容，勿盲目自动拉取 latest。

```sh
# 只构建，不中断服务：
python3 scripts/upgrade.py 版本 官方SHA256
# 停止 Agent 任务后，执行备份并切换：
python3 scripts/upgrade.py 版本 官方SHA256 --apply
```

旧镜像保留，受限备份在 `backups/yyyyMMdd-HHmmss/data.tar.gz`，包含 data 与原 .env，包含敏感认证，不能公开。workspace 不在此快照内，需另外备份项目文件。升级前建议将未提交代码保存到项目自己的 Git/备份。

升级后确认容器健康、客户端配对、项目目录、终端和已授权 Agent。若失败，停止容器，将当前 data 移到其他名称，恢复匹配旧版本的 data/.env 后启动旧镜像；不要用旧程序直接打开已升级数据库。该操作不自动丢弃新版本产生的数据，也不自动进行未经验证的降级。

官方文档：https://orca.dev/docs/remote-servers
官方发行：https://github.com/stablyai/orca/releases
