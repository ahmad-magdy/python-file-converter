# Step 1: Start with a Python base image
FROM python:3.9-slim

# Step 2: Set the working directory
WORKDIR /app

# Step 3: Install system dependencies, including Tesseract OCR
# We update apt-get, install tesseract and its English & Arabic language packs
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ara \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Step 4: Copy the requirements file and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the rest of the application code
COPY . .

# Step 6: Expose the port the app will run on
EXPOSE 8000

# Step 7: Define the command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
