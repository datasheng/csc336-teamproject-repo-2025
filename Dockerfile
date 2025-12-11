FROM python:3.9-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir flask mysql-connector-python python-dotenv werkzeug
CMD ["python", "app.py"]