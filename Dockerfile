FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# HF Spaces requires port 7860 to be exposed
EXPOSE 7860

CMD ["python", "main.py"]
