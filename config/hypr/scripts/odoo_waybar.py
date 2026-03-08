#!/usr/bin/env python3
import json
import os
import sys

# Waybar artik sadece ana uygulamanin hazirladigi metni okur, hesaplama yapmaz.
STATUS_FILE = os.path.expanduser("~/.cache/odoo_status.json")

def main():
    output = {"text": "💼", "tooltip": "Odoo Workspace", "class": "stopped"}
    
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r') as f:
                state = json.load(f)
            
            # Ana uygulamadan gelen hazir formati al
            output["text"] = state.get("display_text", "💼")
            if "running" in state.get("timer", {}):
                output["class"] = "running" if state["timer"]["running"] else "stopped"
        except:
            pass
            
    print(json.dumps(output))
    sys.stdout.flush()

if __name__ == "__main__":
    main()
