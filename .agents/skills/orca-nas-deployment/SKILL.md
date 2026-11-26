---
name: orca-nas-deployment
description: 维护本项目的 Orca 官方 Server Docker 包装、NAS 认证与项目持久化、GitHub 镜像构建和 DSM 备份更新，排查 VERSION 校验、备份 socket 与宿主 ps 兼容问题。
---

# Orca NAS 部署实测

- 使用官方 `orca-server-linux-x64.tar.gz`，不要从桌面 AppImage 提取 Electron 或在 NAS 编译完整 IDE。以官方校验文件验证 SHA256。包自带 Node；1.4.277 实测为 24.22.1，不用镜像系统 Node 替换其运行时。
- `VERSION` 是多行清单，首行为 `orca 版本`，还有 orcad、node、target；用精确行校验，不将整个文件与裸版本字符串比较。
- `/workspace` 是稳定项目路径。`/data/profile` 保存 Orca 项目登记和配对；`/data/home` 保存 Git/Agent 授权；`/data/agents` 保存 Agent 程序。认证不进入镜像、Git 或日志。
- 启动 `orca serve --no-pairing` 避免日志泄漏配对信息。运行后 `orca pair` 可在不重启服务的情况下生成配对，`--mobile` 为手机范围。配对链接是凭据，不输出到开发记录。
- 1.4.277 Server 包只有 mobile-web 资产，实测根路径 404，pair --mobile 的 webClientUrl 为 null；不能把后端健康当成浏览器 IDE 可用。完整桌面远程客户端是另一接入方式，后续网页支持须现场验证。
- DSM Docker 的 PIDs limit 在此内核会被丢弃，不能声称限制生效。`docker top ... -eo args` 宿主不兼容；使用镜像内 procps：`docker exec orca ps -eo args`。
- 停止容器后 profile 仍可能留有 daemon socket。备份只复制普通文件、目录和符号链接，忽略 socket/FIFO/设备；`shutil.copy2` 不保留 UID/GID，恢复快照须显式保留属主，否则非 root 服务无法访问认证目录。
- DSM TaskScheduler API v1 创建任务不能提交 monthly_week，即使读取响应有该字段。此项目安装器已移除；同名任务应幂等复用。
- 构建在 GitHub Actions，NAS 只拉取。更新前识别 Agent 进程、备份，再切换并等待健康；不对升级后的数据库裸降级。自动更新只做服务健康验证，不能宣称所有 Agent 和 UI 均已完成验证。

## Traefik WSS 接入实测（2026/11/26）

- NAS 用 `extends.file` 选择现有 `/volume1/docker/all/compose-presets.yml` 的 web 服务；域名、端口和正则放 NAS .env，使后台更新不依赖 Dockhand 的全局变量注入。仓库内预设仅作便携回退，默认禁用。
- `orca pair --address wss://域名:HTTPS端口 --json` 可生成 HTTPS 代理使用的原生配对链接，实际通过 Traefik 调用官方 CLI status 成功。浏览器根路径仍为404，不能据此判断 WSS 失败。
- `serve --pairing-address wss://...` 能正确宣告 WSS，但本次不传 address 的 `orca pair` 仍选择容器桥接 IP；所以文档和用户命令必须显式传 `--address wss://...`，不能宣称自动选对。
- 容器重建后旧测试配对请求曾返回 remote_runtime_unavailable；重新生成明确WSS地址的配对链接后成功。不要把这条错误直接归因为Traefik路由失效。
- Dockhand 保存镜像时可能将 ORCA_IMAGE 插值改为固定 stable 字符串。确认唯一差异后恢复插值并核对生效镜像不变，否则回退脚本设置 ORCA_IMAGE 不能切换镜像。

## NAS 源码清理约定

Git 仓库与 NAS 运行目录不做全量镜像。NAS 只部署运行 Compose、私有 env、自动更新/安装任务脚本及数据；容器入口和 Agent 安装脚本已在镜像内，不依赖宿主副本。现场清理先对全部候选创建并逐文件校验源码备份，再删除已确认无运行引用的文件；Compose 移除 build 后需比较渲染配置等价。初次直接删除曾被自动审批拒绝；不得绕过，须使用可恢复备份与引用证据。用户自建认证文件和运行数据不清理。

## 代理、npm 与 Agent 沙箱（2026/11/26 实测）

- 官方 1.4.277 的 headless MainHttpClient 使用 bundled Node 24.22.1 fetch；仅存在 HTTP(S)_PROXY 不代表 fetch 使用代理。启动前设置 NODE_USE_ENV_PROXY=1。本次 Google manifest 直连也成功，但 artifact 直连读取超时，代理读取成功，最终安装 Antigravity 1.5.18 且版本命令通过；不能用 manifest 200 代替完整安装验证。
- npm 官方源经过此 NAS 当前代理时 curl TLS 失败、npm ECONNRESET，直连 200；NPM_CONFIG_NOPROXY=registry.npmjs.org 后 npm ping 成功。此为当前链路特例，不泛化为所有 npm 必须直连；不切换第三方镜像或禁用 TLS 来掩盖原因。
- 默认 Agent launch 合并 process.env；Orca 代理、Agent/account env 可以覆盖。Git HTTPS 通过不代表 SSH、账号授权或模型生成通过。Git SSH 不自动使用 HTTP_PROXY。
- Dockhand 页面注入的全局代理不在本地 .env；原生 Compose 自动更新会丢失它。更新器只从旧容器保留代理白名单，通过 subprocess env 传递；本地 .env 显式值和更新进程已有值优先。实测 DSM Compose 2.20.1 没有 config --environment；单引号 env 文件转义与预期不同，不用它中转凭据。用包含 $, 单引号及本地空值覆盖的隔离 Compose fixture 验证，不输出真实配置。
- /workspace 是原始仓库；/data/home/orca/workspaces 是 Git 链接工作树。两者均持久化，不当重复目录清理。
- Codex 缺少 PATH 上的 bwrap 时会使用 bundled helper；加入 bubblewrap 系统依赖后仍需实测 user namespace。不要靠 privileged、关闭沙箱或删除安全参数消除警告。

- 此 DSM 5.10.55+ 上 user namespace 创建成功，但新命名空间内对 / 执行递归 slave 挂载返回 EACCES，bundled bwrap 报 Failed to make / slave: Permission denied。不能将其误报为代理或纯缺包；是否系统包也失败需单独实测，不在未授权情况下扩大宿主/容器权限。
