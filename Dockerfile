FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ListBot.py database.py ./
RUN mkdir -p /app/data
ENV DATA_DIR=/app/data
CMD ["python", "ListBot.py"]
