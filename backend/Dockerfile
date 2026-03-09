# 使用 Python 3.13 作为基础镜像
# 注意：如果遇到镜像拉取问题，可以：
# 1. 尝试使用 python:3.13（非 slim 版本）
# 2. 或使用 Dockerfile.stable（基于 Python 3.12）
ARG BASE_REGISTRY=docker.io
FROM ${BASE_REGISTRY}/library/python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv（快速 Python 包管理器）
RUN pip install uv -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目文件
COPY pyproject.toml uv.lock ./

# 使用 uv 安装依赖
RUN uv sync --frozen -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY main.py ./

# 暴露端口
EXPOSE 8000

# 使用 uv 运行应用
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
