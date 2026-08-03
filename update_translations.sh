#!/bin/bash
mkdir -p po

# 1. Çevrilecek dosya listesini oluştur
cat << 'FILES' > po/files
data/main_window.glade
ui/ui.py
src/cups_backend.py
src/scanner_backend.py
src/notifications.py
src/main.py
FILES

# 2. Python ve Glade dosyalarından kelimeleri ayrı ayrı tara
xgettext --from-code=UTF-8 -k_ -kN_ --language=Python -o po/py_strings.pot ui/ui.py src/*.py 2>/dev/null
xgettext --from-code=UTF-8 --language=Glade -o po/glade_strings.pot data/main_window.glade 2>/dev/null

# 3. İki tarama sonucunu birleştir
msgcat po/py_strings.pot po/glade_strings.pot -o po/eta-printer-manager.pot 2>/dev/null
rm -f po/py_strings.pot po/glade_strings.pot

# 4. tr.po dosyasını sorusuz/otomatik oluştur veya güncelle
if [ -f "po/tr.po" ]; then
    msgmerge -U po/tr.po po/eta-printer-manager.pot
else
    msginit --no-translator --input=po/eta-printer-manager.pot --output=po/tr.po --locale=tr_TR.UTF-8
fi

echo "----------------------------------------"
echo " Success: po/tr.po başarıyla oluşturuldu!"
echo "----------------------------------------"
