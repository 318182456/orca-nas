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
docker compose pull
docker compose up -d --no-build
```

| 宿主目录 | 容器目录 | 保存内容 |
| --- | --- | --- |
| `workspace` | `/workspace` | 原始 Git 项目与未提交文件，项目使用此稳定路径 |
| `data/profile` | `/data/profile` | 项目登记、Orca 配置、会话及配对信息 |
| `data/home` | `/data/home` | Agent 认证、SSH 密钥、Git 配置、GitHub CLI 登录，以及 Orca 创建的 workspaces 链接工作树 |
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

容器不授予 privileged，不挂载 Docker socket，不挂载 NAS 根目录。Agent 可读写挂载的项目与自身凭据，运行任意项目命令前应审阅权限。限制总内存 3 GiB；此 DSM 内核不支持 Docker PIDs 限制；Agent 并发应从 1 开始。ASVS 13.1.1/13.3.2：认证文件不进入源码或镜像，备份也按凭据文件管理。

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

## GitHub 构建与 NAS 自动更新

公开仓库：https://github.com/318182456/orca-nas 。GitHub Actions 每 6 小时检查官方稳定版，校验包后构建 Linux amd64 镜像，发布到 `ghcr.io/318182456/orca-nas:stable` 和版本标签。构建不在 NAS 运行。

NAS 使用 DSM 计划任务每天 05:30 执行 `scripts/auto-update.py`。安装命令：

```sh
sudo python3 scripts/install-task.py
```

手动检查更新：`sudo python3 scripts/auto-update.py`。流程：检测 Agent 进程→拉取镜像→拒绝自动降级→停机→受限备份 data/.env→更新→等待健康。失败时恢复旧镜像及匹配数据，失败的新数据保留以便调查。镜像未变化时不会重建。

备份含认证数据，位于 backups；不要公开。自动更新检查 TCP 服务健康，不能保证每次上游更新都不存在业务兼容问题。Agent 进程检测是保守匹配，无法识别任意自定义程序；需要持续运行长任务时，在 DSM 停用自动更新任务。旧镜像、备份不自动清空。

验证记录（2026/11/26）：GitHub Actions 首次发布成功，镜像匿名拉取返回 200；NAS 切换到 GitHub 镜像、健康检查、PTY 与远程配对 status 均通过；workspace/HOME 文件重建后保留；备份/恢复隔离测试验证 socket 排除及属主、权限、符号链接保留。尚未完成各 Agent 账号首次授权，也未完成完整 IDE 网页验证。

## Traefik 接入

通过 `extends.file` 复用共享 `web` 标签预设；NAS 的 `.env` 可指定 `TRAEFIK_PRESET_FILE=/volume1/docker/all/compose-presets.yml`，保持与其他堆栈一致。仓库内提供禁用状态的便携预设，其他机器无需具备 NAS 的共享目录。独立使用时设置 TRAEFIK_ENABLE=true、域名、HTTPS 端口和网络可达性。

Orca 使用原生配对认证，客户端通过 WSS 建立连接；不在该协议前添加浏览器 SSO 重定向。直连 6768 保持私网绑定。共享预设里的域名和端口参数需在 NAS 本地 .env 可用，避免自动更新依赖 Dockhand 的内存环境。根路径 404 不代表 WebSocket 路由故障，也不意味着完整 IDE 网页可用。

通过 HTTPS 代理配对时，地址需明确使用 WSS（示例域名需替换）：

```sh
docker compose exec orca orca pair --address wss://orca.example.com:8443
```

使用生成的完整配对链接添加远程服务器，不能只把 HTTPS 根地址当作配对码。ORCA_PAIRING_ADDRESS 也可设置为这个 WSS 地址用于服务器对外宣告；直接 6768 端口仍保留私网访问。浏览器根路径返回 404 是当前独立 Server 的已知行为，HTTPS/WSS 配对服务和完整网页 IDE 是不同能力。

注意：本版本在容器中不传 `--address` 的 pair 命令仍可能选择桥接 IP，因此反代客户端配对必须显式指定 WSS 地址，不能只依赖服务器宣告地址。

## NAS 仅部署运行文件

GitHub 构建使用完整仓库；NAS 无需保留 .github/workflows、Dockerfile、源码技能、文档及构建缓存。NAS 的 compose.yaml 移除 build 段，使用 GitHub 发布的镜像，运行参数与数据卷保持原样。

当前 NAS 保留 compose.yaml、.env、scripts/auto-update.py、scripts/install-task.py、data/、workspace/、backups/ 和运行锁；Traefik 预设通过 .env 指向已存在的共享目录，不复制一份。用户自建认证笔记保持原位置，不纳入清理。

后续不能整仓覆盖 NAS；只同步需要的运行文件。首次清理已把原部署源文件备份到 backups/runtime-source-*.tar.gz 并逐文件校验，清理前后的渲染配置除 build 外一致，不重启容器。

## 代理与 Agent 网络

Orca 官方包自带 Node 的 headless fetch 需要 `NODE_USE_ENV_PROXY=1` 才读取 HTTP_PROXY、HTTPS_PROXY 与 NO_PROXY。镜像和 Compose 均启用该开关；只设置代理地址不能保证下载经过代理。代理值由私有 env 或 Dockhand 全局变量注入，不能写入 Git。

Agent 默认继承服务环境，但 Orca 的代理设置、Agent 环境与账号环境可以覆盖继承值。Git HTTPS 使用 HTTP(S) 代理；Git SSH 不会自动使用 HTTP_PROXY，需要单独配置 SSH ProxyCommand 或使用 HTTPS。npm 官方源在本次 NAS 代理链路发生 ECONNRESET、直连成功，因此仅对 registry.npmjs.org 设置 NPM_CONFIG_NOPROXY；Google 下载及模型接口继续使用代理。不要关闭 TLS 校验。

NAS 自动更新通过进程环境保留运行容器的代理白名单；本地 .env 中显式配置优先（包括空值）。不把代理值写入临时文件，不复制其他 Agent 凭据。更新失败仍恢复旧镜像和匹配数据。

`/workspace` 保存原始仓库；`/data/home/orca/workspaces` 是 Orca 创建的 Git 链接工作树，两个路径都持久化。工作树有独立工作文件且共享 Git 对象，不要合并目录或直接删除。

镜像安装系统 bubblewrap，供 Codex 沙箱使用。宿主内核及 Docker 权限仍会影响沙箱可用性；缺少系统程序时的 bundled bubblewrap 提示不等于执行失败，不能通过禁用沙箱或授予 privileged 来隐藏提示。

2026/11/26 实测：Antigravity 下载完成且版本命令返回 1.5.18；Git HTTPS 读取通过，OpenAI/Anthropic 接口收到 HTTP 响应；这些网络检查不代表账号授权或实际模型生成已验证。
