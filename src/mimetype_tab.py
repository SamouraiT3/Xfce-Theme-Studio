import subprocess
from gi.repository import Gtk

# Exécute la commande et récupère la sortie
cmd = "cat /usr/share/mime/globs"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
lines = result.stdout.strip().split("\n")

mime_map = {}

for line in lines:
    if ':' not in line:
        continue
    ext, mime = line.split(":", 1)
    mime_map.setdefault(mime, []).append(ext)

# Prépare les données pour l'interface
items = []  # liste des tuples (mime, texte_complet)
for mime, exts in sorted(mime_map.items()):
    texte = f"{mime}: {', '.join(exts)}"
    # On garde toutes les lignes comme demandé, mais on montre uniquement le mime dans la listbox
    items.append((mime, texte))

# indices valides affichés actuellement
displayed = []

def refresh_list(listbox, search_var, selection=None, handler_id=None):
    query = search_var.get_text().strip().lower()
    
    # Bloquer le signal changed pour éviter un crash si un item est sélectionné
    if selection and handler_id:
        selection.handler_block(handler_id)

    model = listbox.get_model()
    if model is None:
        model = Gtk.ListStore(str)
        listbox.set_model(model)
    else:
        model.clear()

    if selection and handler_id:
        selection.handler_unblock(handler_id)

    displayed.clear()
    for i, (mime, texte) in enumerate(items):
        if not query or query in mime.lower() or query in texte.lower():
            model.append([mime])
            displayed.append(i)

