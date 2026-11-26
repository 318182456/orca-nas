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
