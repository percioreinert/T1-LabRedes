FROM python:3.11-slim

WORKDIR /app
COPY . /app

CMD ["python", "Device.py"]
