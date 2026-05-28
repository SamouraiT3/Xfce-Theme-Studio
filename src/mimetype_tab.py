import subprocess
from gi.repository import Gtk

# Execute the command and capture the output
cmd = "cat /usr/share/mime/globs"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
lines = result.stdout.strip().split("\n")

mime_map = {}

for line in lines:
    if ':' not in line:
        continue
    ext, mime = line.split(":", 1)
    mime_map.setdefault(mime, []).append(ext)

# Prepare the data for the interface
items = []  # list of tuples (mime, full_text)
for mime, exts in sorted(mime_map.items()):
    texte = f"{mime}: {', '.join(exts)}"
    # Keep all lines as requested, but show only the mime in the listbox
    items.append((mime, texte))

# currently displayed valid indices
displayed = []

def refresh_list(listbox, search_var, selection=None, handler_id=None):
    query = search_var.get_text().strip().lower()
    
    # Block the changed signal to avoid a crash if an item is selected
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

