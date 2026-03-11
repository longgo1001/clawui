# TODO.md - My Task List

## Priority: HIGH (Your Direct Instructions)
- (暂无)

## Priority: MEDIUM (Autonomous Tasks)
- [x] 调研并解决 XWayland 与 AT-SPI 不兼容问题（影响 Firefox/Chrome 自动化）- 用户添加
  - [x] 评估现有 backends.py 架构
  - [x] 搜索 Freedesktop Portal for XWayland accessibility
  - [x] 搜索 Marionette/CDP 集成方案
  - [x] 决定实施路线（混合感知 or 切换到 X11）
  - **结论：**
    - XWayland 应用确实无法被 AT-SPI 访问（Wayland 安全模型）
    - Freedesktop Accessibility Portal 仅支持原生 Wayland 应用
    - 成熟方案：浏览器原生协议（CDP for Chromium, Marionette for Firefox）
    - 多后端扩展：atspi (Wayland) + x11 (xdotool/XWayland) + cdp/marionette
    - 临时方案：切换用户到 X11 会话（最快）
- [x] 测试 gui-automation 技能基本功能（UI 树正常）
- [x] 创建 heartbeat cron 作业（每30分钟检查）
- [ ] 编写端到端测试脚本
- [x] 完善 README 使用示例  # 注意：此处可能标记有误，实际未完善
- [ ] 配置 git 凭据以推送仓库（需用户提供信息）
- [ ] 实现 CDP 后端支持 Chromium 浏览器
- [ ] 实现 Marionette 后端支持 Firefox
- [ ] 重构 backends.py 支持多感知模式自动选择

## Priority: LOW (When Idle)
- [x] 审查 MEMORY.md 并更新
- [x] 优化技能元数据
- [x] 补充 PROGRESS.md 详细进度

---

Last checked: 2026-03-11 08:15 (GMT+8)
Next check: cron trigger (every 30 minutes)