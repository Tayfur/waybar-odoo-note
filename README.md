# 💼 Odoo Hyprland Hub

A premium, Gruvbox-themed productivity suite for Hyprland users. Integrated directly into Waybar, this hub provides a seamless workflow for Odoo Attendances, Timesheets, and Quick Notes.

![Preview](https://via.placeholder.com/850x550.png?text=Odoo+Workspace+Preview)

## ✨ Features
- **Modern Dashboard:** Dual-column GTK3 interface with Odoo controls and daily activity logs.
- **Live Waybar Tracking:** Real-time feedback on your Waybar: `Proje-Task 00:15 | 🟢 04:30`.
- **Auto-Sync:** Fetches projects, tasks, and history automatically on startup.
- **Smart Attendance:** One-click Check-in/Out with live time calculation.
- **Quick Notes:** Independent minimalist notes modal.

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone (https://github.com/Tayfur/waybar-odoo-note.git)
   cd odoo-hypr-hub
   ```

2. **Run the installer:**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Configure Odoo:**
   Copy `.env.example` to `~/.config/odoo-hypr-modal/.env` and fill in your details.

## 🛠 Requirements
- `hyprland`
- `waybar`
- `python-gobject` (gi)
- `python-dotenv`
- `yad` (for notes)

---
Developed by **Tayfur** with ☕ and Arch Linux.
