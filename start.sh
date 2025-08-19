cat > start.sh << 'EOF'
#!/bin/bash
pip install --upgrade -r requirements.txt
python3 -m flask run
EOF
chmod +x start.sh
