#!/usr/bin/env bash
set -Eeuo pipefail

# 重启 Wine 微信开发者工具，并尽量自动进入项目
# 目标项目：C:\users\hung\WeChatProjects\miniprogram-1

export WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"
export DISPLAY="${DISPLAY:-:0}"

PROJECT_WIN_PATH='C:\users\hung\WeChatProjects\miniprogram-1'
PROJECT_UNIX_PATH="$WINEPREFIX/drive_c/users/hung/WeChatProjects/miniprogram-1"
STAMP="$(date +%Y%m%d_%H%M%S)"
SHOT_DIR="/tmp"
LOG_PREFIX="[wechat-recover]"

log() { echo "$LOG_PREFIX $*"; }
warn() { echo "$LOG_PREFIX WARN: $*" >&2; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "$LOG_PREFIX ERROR: missing command: $1" >&2
    exit 1
  }
}

snap() {
  local tag="${1:-shot}"
  local out="$SHOT_DIR/wechat_recover_${STAMP}_${tag}.png"

  if command -v import >/dev/null 2>&1; then
    import -window root "$out" >/dev/null 2>&1 || true
  elif command -v gnome-screenshot >/dev/null 2>&1; then
    gnome-screenshot -f "$out" >/dev/null 2>&1 || true
  elif command -v scrot >/dev/null 2>&1; then
    scrot "$out" >/dev/null 2>&1 || true
  fi

  if [[ -f "$out" ]]; then
    log "screenshot: $out"
  else
    warn "screenshot failed for tag=$tag"
  fi
}

cleanup_processes() {
  log "清理残留进程 (wine/nw/wechatdevtools)..."

  # 先温和，再强制
  pkill -f 'wechatdevtools\.exe|微信web开发者工具|code/package\.nw|\bnw\.exe\b' >/dev/null 2>&1 || true
  sleep 2
  pkill -9 -f 'wechatdevtools\.exe|微信web开发者工具|code/package\.nw|\bnw\.exe\b' >/dev/null 2>&1 || true

  # 清理可能残留的 wine server（不影响其他前台任务时才建议执行）
  wineserver -k >/dev/null 2>&1 || true
  sleep 1
}

find_launcher() {
  local candidates=(
    "$HOME/launch_wechat_devtools.sh"
    "$HOME/.openclaw/workspace/tools/launch_wechat_devtools.sh"
  )

  for c in "${candidates[@]}"; do
    if [[ -x "$c" ]]; then
      echo "$c"
      return 0
    fi
  done

  # 如果脚本不可执行但存在，也可用 bash 调
  for c in "${candidates[@]}"; do
    if [[ -f "$c" ]]; then
      echo "bash $c"
      return 0
    fi
  done

  return 1
}

launch_wechat() {
  log "启动微信开发者工具..."
  local launcher
  if launcher="$(find_launcher)"; then
    log "使用启动器: $launcher"
    # shellcheck disable=SC2086
    nohup $launcher >/tmp/wechat_recover_launch_${STAMP}.log 2>&1 &
    return 0
  fi

  # 回退：直接 wine 启动常见安装路径
  local app_dir="$WINEPREFIX/drive_c/Program Files (x86)/Tencent/微信web开发者工具"
  local exe1="$app_dir/wechatdevtools.exe"
  local exe2="$HOME/wechat-tools/wechatdevtools.exe"
  local exe3="$HOME/wechat-tools/wechat_devtools.exe"

  if [[ -f "$exe1" ]]; then
    (cd "$app_dir" && nohup wine wechatdevtools.exe "code/package.nw" --no-sandbox --use-gl=swiftshader >/tmp/wechat_recover_launch_${STAMP}.log 2>&1 &) || true
    return 0
  elif [[ -f "$exe2" ]]; then
    nohup wine "$exe2" >/tmp/wechat_recover_launch_${STAMP}.log 2>&1 &
    return 0
  elif [[ -f "$exe3" ]]; then
    nohup wine "$exe3" >/tmp/wechat_recover_launch_${STAMP}.log 2>&1 &
    return 0
  fi

  warn "未找到可用启动方式，请先确认安装路径"
  return 1
}

wait_window() {
  local timeout="${1:-60}"
  local start now wid
  start="$(date +%s)"

  log "等待窗口出现 (最多 ${timeout}s)..."
  while true; do
    wid="$(xdotool search --name '微信开发者工具|WeChat DevTools|微信Web开发者工具' 2>/dev/null | head -n1 || true)"
    if [[ -n "$wid" ]]; then
      echo "$wid"
      return 0
    fi

    now="$(date +%s)"
    if (( now - start >= timeout )); then
      return 1
    fi
    sleep 1
  done
}

activate_window() {
  local wid="$1"
  xdotool windowactivate --sync "$wid" 2>/dev/null || true
  xdotool windowsize "$wid" 1280 800 2>/dev/null || true
  xdotool windowraise "$wid" 2>/dev/null || true
}

try_open_import_or_create() {
  local wid="$1"
  log "尝试触发 导入/新建..."

  # 常见快捷键尝试：导入项目 / 新建项目
  xdotool key --window "$wid" --delay 80 ctrl+i 2>/dev/null || true
  sleep 1
  xdotool key --window "$wid" --delay 80 ctrl+n 2>/dev/null || true
  sleep 1

  # 兜底：Alt+F 后 I/N（英文菜单习惯）
  xdotool key --window "$wid" --delay 80 alt+f 2>/dev/null || true
  sleep 0.6
  xdotool key --window "$wid" --delay 80 i 2>/dev/null || true
  sleep 1
  xdotool key --window "$wid" --delay 80 alt+f 2>/dev/null || true
  sleep 0.6
  xdotool key --window "$wid" --delay 80 n 2>/dev/null || true
  sleep 1
}

try_toggle_no_cloud() {
  local wid="$1"
  log "尝试切换“不使用云服务”(按键兜底，界面差异可能导致失败)..."

  # 先尝试可能存在的快捷键
  xdotool key --window "$wid" --delay 80 alt+s 2>/dev/null || true
  sleep 0.6

  # 再尝试 tab 导航 + 空格（常见勾选框操作）
  # 注意：这里是启发式，不保证每个版本都命中
  for _ in 1 2 3 4 5 6; do
    xdotool key --window "$wid" Tab 2>/dev/null || true
    sleep 0.15
  done
  xdotool key --window "$wid" space 2>/dev/null || true
  sleep 0.5
}

try_fill_project_path() {
  local wid="$1"
  log "尝试填写项目路径并确认导入..."

  # 尝试切到路径输入框（启发式多次 Tab）
  for _ in 1 2 3 4 5; do
    xdotool key --window "$wid" Tab 2>/dev/null || true
    sleep 0.12
  done

  # Ctrl+A 清空后输入 Windows 路径
  xdotool key --window "$wid" ctrl+a 2>/dev/null || true
  sleep 0.2
  xdotool type --window "$wid" --delay 8 "$PROJECT_WIN_PATH" 2>/dev/null || true
  sleep 0.3

  # 再输入一次 Unix 路径作为兜底（某些对话框接受 Linux 路径）
  xdotool key --window "$wid" Return 2>/dev/null || true
  sleep 0.5
  xdotool key --window "$wid" ctrl+a 2>/dev/null || true
  sleep 0.2
  xdotool type --window "$wid" --delay 8 "$PROJECT_UNIX_PATH" 2>/dev/null || true
  sleep 0.3

  # 尝试确认
  xdotool key --window "$wid" Return 2>/dev/null || true
}

main() {
  need_cmd wine
  need_cmd wineserver
  need_cmd xdotool

  if ! xdpyinfo >/dev/null 2>&1; then
    warn "当前 DISPLAY=$DISPLAY 不可用，GUI 自动化可能失败"
  fi

  if [[ ! -d "$PROJECT_UNIX_PATH" ]]; then
    warn "项目目录不存在: $PROJECT_UNIX_PATH"
  fi

  cleanup_processes
  snap "after_cleanup"

  launch_wechat || {
    snap "launch_failed"
    exit 2
  }

  local wid
  if ! wid="$(wait_window 75)"; then
    warn "等待窗口超时，查看日志: /tmp/wechat_recover_launch_${STAMP}.log"
    snap "window_timeout"
    exit 3
  fi

  log "窗口已出现: WID=$wid"
  activate_window "$wid"
  sleep 1
  snap "window_ready"

  try_open_import_or_create "$wid"
  sleep 1
  snap "after_open_import_or_create"

  try_toggle_no_cloud "$wid"
  snap "after_toggle_no_cloud"

  try_fill_project_path "$wid"
  sleep 1
  snap "after_try_import"

  log "完成：已执行重启 + 自动导入尝试。"
  log "截图位置: /tmp/wechat_recover_${STAMP}_*.png"
  log "启动日志: /tmp/wechat_recover_launch_${STAMP}.log"
}

main "$@"
