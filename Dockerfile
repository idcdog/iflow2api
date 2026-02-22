# iFlow2API Dockerfile
# 多阶段构建，优化镜像大小，并兼容 Docker/Compose 生产部署

# 阶段1：构建依赖（基于 uv.lock 做可复用缓存）
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# 仅复制依赖清单，最大化 Docker layer 缓存命中
COPY pyproject.toml uv.lock README.md ./

# 安装依赖到虚拟环境（不安装当前项目本体，避免缺少源码导致失败）
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv sync --frozen --no-dev --active --no-install-project


# 阶段2：运行镜像
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# 创建运行用户（固定 UID/GID，便于宿主机挂载时对齐权限）
ARG APP_UID=10001
ARG APP_GID=10001
RUN groupadd -g "${APP_GID}" appuser \
    && useradd -m -u "${APP_UID}" -g "${APP_GID}" -s /bin/bash appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码与容器启动脚本
COPY . .
RUN chmod +x /app/docker/entrypoint.sh

# 运行期默认配置（可被 docker-compose 环境变量覆盖）
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=28000

EXPOSE 28000

# 允许通过 PORT 环境变量变更健康检查端口（使用 shell form 以支持变量展开）
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-28000}/health" || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["python", "-m", "iflow2api"]
