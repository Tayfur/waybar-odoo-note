#!/bin/bash
mkdir -p "$HOME/Notes"
FILE="$HOME/Notes/quick_note.txt"
touch "$FILE"

# Yad ile bir not penceresi açılır. --filename sayesinde mevcut notlar içine yüklenir.
NEW_CONTENT=$(yad --text-info \
    --title="Hızlı Notlar" \
    --width=500 --height=400 \
    --filename="$FILE" \
    --editable \
    --wrap \
    --button="Kaydet ve Kapat:0" \
    --button="İptal:1" \
    --window-icon=accessories-text-editor \
    --center \
    --borders=15)

# Eğer kullanıcı "Kaydet ve Kapat" butonuna basarsa (yad exit code 0 döner)
if [ $? -eq 0 ]; then
    # \n (yeni satır) karakterlerinin doğru işlenmesi için printf kullanıyoruz
    printf "%s\n" "$NEW_CONTENT" > "$FILE"
fi