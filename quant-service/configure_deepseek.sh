#!/bin/sh
set -eu
cd "$(dirname "$0")"

printf "请输入 DeepSeek API Key（输入不会显示）: "
stty -echo
IFS= read -r deepseek_key
stty echo
printf "\n"

case "$deepseek_key" in
  sk-*) ;;
  *) printf "密钥格式不正确，应以 sk- 开头。\n" >&2; exit 1 ;;
esac

env_file=".env"
temp_file="$(mktemp)"
trap 'rm -f "$temp_file"' EXIT
if [ -f "$env_file" ]; then
  awk '!/^DEEPSEEK_API_KEY=/ && !/^DEEPSEEK_MODEL=/' "$env_file" > "$temp_file"
fi
printf "\nDEEPSEEK_API_KEY=%s\nDEEPSEEK_MODEL=deepseek-v4-flash\n" "$deepseek_key" >> "$temp_file"
chmod 600 "$temp_file"
mv "$temp_file" "$env_file"
trap - EXIT
printf "DeepSeek 已配置为 deepseek-v4-flash，密钥仅保存在 quant-service/.env。\n"
