#!/bin/sh
set -eu

APP_USER="appuser"
APP_HOME="/home/${APP_USER}"

# gosu 不会自动切换 HOME，手动设置以确保 Path.home() 指向正确目录
export HOME="${APP_HOME}"

IFLOW_DIR="${APP_HOME}/.iflow"
IFLOW_SETTINGS_JSON="${IFLOW_DIR}/settings.json"
IFLOW2API_DIR="${APP_HOME}/.iflow2api"
IFLOW2API_CONFIG_JSON="${IFLOW2API_DIR}/config.json"

mkdir -p "${IFLOW_DIR}" "${IFLOW2API_DIR}"

if [ "$(id -u)" -eq 0 ]; then
  chown -R "${APP_USER}:${APP_USER}" "${IFLOW_DIR}" "${IFLOW2API_DIR}" 2>/dev/null || true
fi

# 通过环境变量覆盖 iflow2api 应用配置（写入 ~/.iflow2api/config.json）
# 仅当提供对应环境变量时才会写入/更新。
if [ -n "${IFLOW2API_CUSTOM_API_KEY:-}" ] || [ -n "${IFLOW2API_CUSTOM_AUTH_HEADER:-}" ] || [ -n "${IFLOW2API_API_CONCURRENCY:-}" ] || [ -n "${IFLOW2API_PRESERVE_REASONING_CONTENT:-}" ]; then
  tmp_file="$(mktemp)"
  IFLOW2API_CONFIG_PATH="${IFLOW2API_CONFIG_JSON}" python - <<'PY' > "${tmp_file}"
import json
import os
from pathlib import Path

path = Path(os.environ["IFLOW2API_CONFIG_PATH"])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        data = {}
except Exception:
    data = {}

def set_if(env_name: str, key: str, cast: str | None = None) -> None:
    raw = os.environ.get(env_name)
    if raw is None or raw == "":
        return
    if cast == "int":
        value = int(raw)
    elif cast == "bool":
        value = raw.strip().lower() in ("1", "true", "yes", "y", "on")
    else:
        value = raw
    data[key] = value

set_if("IFLOW2API_CUSTOM_API_KEY", "custom_api_key")
set_if("IFLOW2API_CUSTOM_AUTH_HEADER", "custom_auth_header")
set_if("IFLOW2API_API_CONCURRENCY", "api_concurrency", cast="int")
set_if("IFLOW2API_PRESERVE_REASONING_CONTENT", "preserve_reasoning_content", cast="bool")

print(json.dumps(data, ensure_ascii=False, indent=2))
PY

  if [ "$(id -u)" -eq 0 ]; then
    install -o "${APP_USER}" -g "${APP_USER}" -m 600 "${tmp_file}" "${IFLOW2API_CONFIG_JSON}"
    rm -f "${tmp_file}"
  else
    mv "${tmp_file}" "${IFLOW2API_CONFIG_JSON}"
    chmod 600 "${IFLOW2API_CONFIG_JSON}" 2>/dev/null || true
  fi
fi

# 通过环境变量写入 iFlow 配置（满足 docs/DOCKER.md 的部署方式）
# - IFLOW_API_KEY：必填（启用后才会写入）
# - IFLOW_BASE_URL：可选，默认 https://apis.iflow.cn/v1
# - IFLOW_AUTH_TYPE：可选，默认 api-key（可用 oauth-iflow）
# - IFLOW_API_KEY_FORCE=1：强制覆盖现有 settings.json
if [ -n "${IFLOW_API_KEY:-}" ]; then
  if [ ! -f "${IFLOW_SETTINGS_JSON}" ] || [ "${IFLOW_API_KEY_FORCE:-0}" = "1" ]; then
    tmp_file="$(mktemp)"
    python - <<'PY' > "${tmp_file}"
import json
import os

api_key = os.environ["IFLOW_API_KEY"]
base_url = os.environ.get("IFLOW_BASE_URL") or "https://apis.iflow.cn/v1"
auth_type = os.environ.get("IFLOW_AUTH_TYPE") or "api-key"

data = {
    "apiKey": api_key,
    "baseUrl": base_url,
    "selectedAuthType": auth_type,
}
print(json.dumps(data, ensure_ascii=False, indent=2))
PY

    if [ "$(id -u)" -eq 0 ]; then
      install -o "${APP_USER}" -g "${APP_USER}" -m 600 "${tmp_file}" "${IFLOW_SETTINGS_JSON}"
      rm -f "${tmp_file}"
    else
      mv "${tmp_file}" "${IFLOW_SETTINGS_JSON}"
      chmod 600 "${IFLOW_SETTINGS_JSON}" 2>/dev/null || true
    fi
  fi
fi

# 默认启动命令（允许用户在 compose/CLI 中覆盖）
if [ "$#" -eq 0 ]; then
  set -- python -m iflow2api
fi

# 若用户启动的是 iflow2api 服务进程，则补齐 host/port 参数
case "$1" in
  iflow2api|python|python3)
    has_host=0
    has_port=0
    for arg in "$@"; do
      [ "$arg" = "--host" ] && has_host=1
      [ "$arg" = "--port" ] && has_port=1
    done
    if [ "${has_host}" -eq 0 ]; then
      set -- "$@" --host "${HOST:-0.0.0.0}"
    fi
    if [ "${has_port}" -eq 0 ]; then
      set -- "$@" --port "${PORT:-28000}"
    fi
    ;;
esac

if [ "$(id -u)" -eq 0 ]; then
  exec gosu "${APP_USER}" "$@"
else
  exec "$@"
fi
