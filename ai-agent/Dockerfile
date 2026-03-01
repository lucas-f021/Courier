FROM python:3.11

WORKDIR /app

# Compile the C base64 decoder for Linux
COPY base64.c .
RUN gcc -O2 -shared -fPIC -o b64decode.so base64.c

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Unbuffered output so logs appear immediately in docker logs
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY . .

EXPOSE 5000

CMD ["python", "main.py"]
