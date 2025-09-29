FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 只复制requirements文件来安装依赖
COPY requirements.txt /tmp/requirements.txt

# 安装Python依赖
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# 创建模型目录
RUN mkdir -p /app/Kronos_model

# 暴露端口（如果需要web服务）
EXPOSE 8000

# 本地部署模式 - 不需要 Git 配置

# 运行主程序
CMD ["python", "update_predictions.py"]