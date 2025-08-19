#!/bin/bash
# Install system packages (needed once per repl)
if ! command -v tesseract &> /dev/null
then
  echo "Installing Tesseract..."
  apt-get update -y
  apt-get install -y tesseract-ocr
fi

# Install Python packages
pip install --upgrade flask pillow img2pdf pytesseract PyMuPDF

# Start Flask
python3 -m flask run
