FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy plugin source from repo root
COPY . /plugin-source/

# Install the plugin in editable mode with vault extras
RUN cd /plugin-source && pip install -e ".[vault]"

# Copy client requirements and install additional dependencies
COPY examples/vault-nginx-mlflow/client/requirements.txt .
RUN pip install -r requirements.txt

# Copy demo script
COPY examples/vault-nginx-mlflow/client/demo.py .

CMD ["python", "demo.py"]
