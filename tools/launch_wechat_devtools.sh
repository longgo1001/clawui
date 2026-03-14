#!/bin/bash
# 微信开发者工具 Wine 启动脚本
cd "/home/hung/.wine/drive_c/Program Files (x86)/Tencent/微信web开发者工具/"
WINEPREFIX="$HOME/.wine" wine wechatdevtools.exe "code/package.nw" \
  --no-sandbox --disable-gpu --disable-gpu-compositing --in-process-gpu 2>/dev/null &
echo "微信开发者工具已启动"
