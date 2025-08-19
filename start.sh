#!/bin/bash
# Install system packages (needed once per repl)
if ! command -v tesseract &> /dev/null
then
  echo "Installing Tesseract..."
  apt-get update -y
  apt-get install -y tesseract-ocr
fi

# Install Python packages from requirements.txt
pip install --upgrade -r requirements.txt

# Start Flask
python3 -m flask run
