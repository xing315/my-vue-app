#!/bin/sh
set -eu
cd "$(dirname "$0")"
target="$HOME/Library/LaunchAgents/com.zhangspace.quant-sync.plist"
mkdir -p "$HOME/Library/LaunchAgents" data/logs
cp com.zhangspace.quant-sync.plist "$target"
launchctl bootout "gui/$(id -u)/com.zhangspace.quant-sync" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$target"
echo "Installed: $target (daily at 16:45, weekends skipped)"
