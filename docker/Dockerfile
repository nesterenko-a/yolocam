FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    mkdir -p /root/.insightface/models /root/.config/Ultralytics && \
    echo '{"settings_version":"0.0.6","datasets_dir":"/root/.config/Ultralytics"}' > /root/.config/Ultralytics/settings.json

ENV YOLO_CONFIG_DIR=/root/.config/Ultralytics
ENV YOLO_HEADLESS=true
ENV YOLO_WEB_STREAM=true
ENV YOLO_WEB_PORT=8080
ENV ORT_LOG_SEVERITY_LEVEL=3
ENV YOLO_CAMERA=http://10.8.1.1:8081/stream
COPY . .

EXPOSE 8080

CMD ["python", "app.py"]
