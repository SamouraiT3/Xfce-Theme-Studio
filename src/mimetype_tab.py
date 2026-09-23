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

def refresh_list(listbox, search_var, selection=None, handler_id=None, category="All"):
    query = search_var.get_text().strip().lower()
    category = category or "All"
    
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
        if category and category != "All":
            category_lower = category.lower()
            if category_lower == "images" and not mime.lower().startswith("image/"):
                continue
            if category_lower == "audio" and not mime.lower().startswith("audio/"):
                continue
            if category_lower == "video" and not mime.lower().startswith("video/"):
                continue
            if category_lower == "documents" and not (
                mime.lower().startswith("text/")
                or mime.lower().startswith("application/pdf")
                or mime.lower().startswith("application/msword")
                or mime.lower().startswith("application/vnd")
                or mime.lower().startswith("application/rtf")
                or mime.lower().startswith("application/xml")
            ):
                continue
            if category_lower == "archives" and not (
                mime.lower().startswith("application/zip")
                or mime.lower().startswith("application/x-rar")
                or mime.lower().startswith("application/gzip")
                or mime.lower().startswith("application/x-7z")
                or mime.lower().startswith("application/x-tar")
                or mime.lower().endswith(".zip")
            ):
                continue
            if category_lower == "code" and not (
                mime.lower().startswith("text/")
                or mime.lower().startswith("application/json")
                or mime.lower().startswith("application/javascript")
                or mime.lower().startswith("application/x-python")
                or mime.lower().startswith("application/xml")
                or mime.lower().endswith("+json")
                or mime.lower().endswith("+xml")
            ):
                continue

        if not query or query in mime.lower() or query in texte.lower():
            model.append([mime])
            displayed.append(i)

