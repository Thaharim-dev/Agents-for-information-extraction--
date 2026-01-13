# 1. Use an official Python image
FROM python:3.10-slim

# 2. Install Tesseract OCR and system dependencies for PDF processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && apt-get clean

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Copy your agent code into the container
COPY agent_service.py .

# 5. Install Python libraries directly
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    pdf2image \
    pytesseract \
    networkx \
    pillow

# 6. Expose the port FastAPI runs on
EXPOSE 8000

# 7. Command to run the agent
CMD ["uvicorn", "agent_service:app", "--host", "0.0.0.0", "--port", "8000"]
