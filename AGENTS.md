# 项目维护规则

- 本项目只包装官方 Orca Server，不 fork 桌面主程序；升级固定版本并验证官方包 SHA256。
- NAS 代码目录 /volume1/docker/orca；项目必须使用容器内稳定路径 /workspace。
- data/home、data/profile、data/agents 和 workspace 均是持久数据，禁止在构建、升级或清理中删除。
- 不提交 .env、认证文件、SSH 密钥、配对码、会话或用户项目；日志不打印配对链接。
- Agent CLI 更新独立于 Orca；精确记录版本，认证按各家官方流程，不擅自复制其他服务凭据。
- 升级先构建候选、停止 Agent 任务、备份配置，再切换；数据库降级必须恢复配套备份。
- 验证至少包括启动健康、PTY、项目读写及重建持久化。网页验证使用 Playwright MCP。
- 无桌面、无 Docker socket、无 NAS 根目录挂载；直连端口仅内网或 Tailscale；用户授权的 Traefik WSS 入口保留 Orca 原生配对认证，不添加破坏客户端协议的网页重定向。

## NAS 运行目录边界

- GitHub Workflow、构建源码、Dockerfile、开发技能与文档仅保留在 Git 仓库；不再整仓同步到 NAS。
- NAS 只保留 compose.yaml、.env、scripts/auto-update.py、scripts/install-task.py、data、workspace、backups 和运行锁；用户自建文件（如认证笔记）不得擅自删除。
- NAS Compose 不包含 build，当前通过 .env 指定外部共享 Traefik 预设；它与仓库开发用 Compose 有意不同，不以逐字镜像覆盖。
- 同步只更新实际运行需要的文件；不重新上传 .github、.agents、.cache 或镜像内自带的入口脚本。
- 清理前验证容器挂载和更新任务实际引用，创建并校验可恢复备份；移除 build 后比较完整渲染配置，除 build 外必须等价。保留全部运行数据和凭据。
