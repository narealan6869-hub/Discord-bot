FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg

COPY requirements_hosted.txt .
RUN pip install --no-cache-dir -r requirements_hosted.txt

COPY discord_bot_hosted.py .
COPY tickets.json .

CMD ["python", "discord_bot_hosted.py"]
