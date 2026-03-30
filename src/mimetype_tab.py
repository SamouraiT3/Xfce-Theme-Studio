import subprocess
import tkinter as tk
from tkinter import messagebox

# Exécute la commande et récupère la sortie
cmd = "cat /usr/share/mime/globs"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
lines = result.stdout.strip().split("\n")

mime_map = {}

for line in lines:
    if ':' not in line:
        continue
    ext, mime = line.split(":", 1)
    mime_map.setdefault(mime, []).append(ext)  # type: ignore

# Prépare les données pour l'interface
items = []  # liste des tuples (mime, texte_complet)
for mime, exts in sorted(mime_map.items()):  # type: ignore
    texte = f"{mime}: {', '.join(exts)}"
    # On garde toutes les lignes comme demandé, mais on montre uniquement le mime dans la listbox
    items.append((mime, texte))

# indices valides affichés actuellement
displayed = []

def refresh_list(listbox, search_var):
    query = search_var.get().strip().lower()
    listbox.delete(0, tk.END)
    displayed.clear()
    for i, (mime, texte) in enumerate(items):
        if not query or query in mime.lower() or query in texte.lower():
            listbox.insert(tk.END, mime)
            displayed.append(i)


def on_select(event):
    if not listbox.curselection():
        return
    idx = listbox.curselection()[0]
    item_index = displayed[idx]
    mime, texte = items[item_index]
    messagebox.showinfo(f"Détails pour {mime}", texte)

