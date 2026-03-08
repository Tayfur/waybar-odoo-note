#!/bin/bash

echo "🚀 Starting Odoo Hyprland Hub Installation..."

# 1. Klasörleri Oluştur
mkdir -p ~/.config/waybar/themes/tayfur-custom
mkdir -p ~/.config/hypr/scripts
mkdir -p ~/odoo-hypr-modal

# 2. Dosyaları Yerleştir
cp -r config/waybar/themes/tayfur-custom/* ~/.config/waybar/themes/tayfur-custom/
cp config/hypr/scripts/* ~/.config/hypr/scripts/
cp src/* ~/odoo-hypr-modal/

# 3. İzinleri Ayarla
chmod +x ~/.config/hypr/scripts/*.sh
chmod +x ~/.config/hypr/scripts/*.py
chmod +x ~/odoo-hypr-modal/main.py

# 4. Hyprland Konfigürasyonu (Eğer yoksa ekle)
if ! grep -q "OdooModal" ~/.config/hypr/conf/custom.conf; then
    echo "Adding Hyprland Window Rules..."
    cat << 'EOF' >> ~/.config/hypr/conf/custom.conf

# Odoo & Notes Modal Window Rules
windowrule {
    name = odoomodal
    match:class = (.*main\.py.*)
    match:title = (.*Odoo Workspace.*)
    float = true
    center = true
    size = 900 600
}

windowrule {
    name = yadnotes
    match:class = (.*yad.*)
    match:title = (.*Hızlı Notlar.*)
    float = true
    center = true
    size = 500 400
}
EOF
fi

echo "✅ Installation complete! Please edit ~/odoo-hypr-modal/.env with your Odoo credentials."
