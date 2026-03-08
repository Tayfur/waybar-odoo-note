#!/bin/bash
# Odoo & Notes uygulamasını açıp kapatan (toggle) script

if pgrep -f "python.*odoo-hypr-modal/main.py" > /dev/null; then
    # Eğer açıksa kapat
    pkill -f "python.*odoo-hypr-modal/main.py"
else
    # Eğer kapalıysa aç
    ~/odoo-hypr-modal/venv/bin/python ~/odoo-hypr-modal/main.py &
fi