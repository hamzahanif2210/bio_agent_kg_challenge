FROM python:3.11-slim
WORKDIR /app
COPY requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt
COPY src ./src
COPY sample ./sample
ENV PYTHONPATH=/app/src HOST=0.0.0.0 PORT=10000
EXPOSE 10000
CMD ["python", "-m", "bioagent", "--graph", "sample/sample.whole", "serve"]
