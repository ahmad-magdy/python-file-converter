#!/bin/bash
echo "🔄 Pulling latest changes from GitHub..."
git reset --hard
git pull origin main

echo "📦 Installing Python dependencies (user mode)..."
python3 -m pip install --user -r requirements.txt

echo "✅ Update complete!"
