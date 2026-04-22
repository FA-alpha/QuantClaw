FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY app.py .

# 创建数据目录
RUN mkdir -p /app/data

# 环境变量
ENV QUANTCLAW_DATA_DIR=/app/data
ENV QUANTCLAW_HOST=0.0.0.0
ENV QUANTCLAW_PORT=5000

EXPOSE 5000

# 运行
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
