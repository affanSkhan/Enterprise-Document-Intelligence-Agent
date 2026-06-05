FROM python:3.10-slim

WORKDIR /app

# Required for PyMuPDF and other parsers
RUN apt-get update && apt-get install -y build-essential

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
