import os
from pathlib import Path
from gi.repository import Gtk, GdkPixbuf

# 🔹 1. Choisir meilleure icône
def best_icon(file_list):
    best = None
    best_size = -1
    svg = None

    for f in file_list:
        ext = os.path.splitext(f)[1].lower()

        if ext == ".svg":
            svg = f
            continue

        size = 0
        parts = f.split(os.sep)
        for p in parts:
            if "x" in p and p.split("x")[0].isdigit():
                size = int(p.split("x")[0])
                break

        if size > best_size:
            best_size = size
            best = f

    return best if best else svg


# 🔹 2. Scanner un thème pour une catégorie
def scan_category(theme_dir, category):
    icons = {}

    for root, dirs, files in os.walk(theme_dir):
        # IMPORTANT : vérifier si le chemin contient la catégorie
        if category.lower() not in root.lower():
            continue

        for f in files:
            name, ext = os.path.splitext(f)
            if ext.lower() not in [".png", ".svg", ".xpm"]:
                continue

            full_path = os.path.join(root, f)

            if name not in icons:
                icons[name] = []
            icons[name].append(full_path)

    result = {}
    for name, files in icons.items():
        result[name] = best_icon(files)

    return result


# 🔹 3. Lister toutes les icônes avec héritage
def list_icon(category, theme_dirs):
    final_icons = {}

    for theme in theme_dirs:
        icons = scan_category(theme, category)

        for name, path in icons.items():
            if name not in final_icons:
                final_icons[name] = path

    return list(final_icons.values())


# 🔹 4. Affichage dans GTK
def display_icon(container, paths, load_image, on_click, grid_cols=1):
    # Clear existing children - Gtk.Grid uses foreach to iterate
    def remove_child(child):
        container.remove(child)
    container.foreach(remove_child)

    photo_refs = []
    icon_items = []

    for idx, path in enumerate(paths):
        row, col = divmod(idx, grid_cols)

        # Create EventBox to capture click events
        event_box = Gtk.EventBox()
        event_box.set_margin_start(6)
        event_box.set_margin_end(6)
        event_box.set_margin_top(6)
        event_box.set_margin_bottom(6)
        event_box.set_visible(True)
        
        # Attach to grid
        container.attach(event_box, col, row, 1, 1)

        # Create Frame inside EventBox for visual styling
        cell = Gtk.Frame()
        cell.set_shadow_type(Gtk.ShadowType.IN)
        event_box.add(cell)

        # Create vertical box for content
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_start(4)
        vbox.set_margin_end(4)
        vbox.set_margin_top(4)
        vbox.set_margin_bottom(4)
        cell.add(vbox)

        # Load and display image
        img = load_image(path, (64, 64))
        
        if img:
            # Scale to 64x64
            img = img.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)
            img_widget = Gtk.Image.new_from_pixbuf(img)
        else:
            img_widget = Gtk.Label(label="X")
        
        vbox.pack_start(img_widget, False, False, 0)

        # Add click handler - connect to event_box
        def make_callback(p=path, c=event_box, i=img):
            def callback(widget, event):
                on_click(p, c, i)
            return callback
        
        handler_id = event_box.connect("button-press-event", make_callback())

        # Store reference - use event_box as cell reference
        icon_items.append({
            "path": path,
            "cell": event_box,
            "handler_id": handler_id
        })

    container.show_all()
    return icon_items, photo_refs


# 🔹 5. Clic onglet
def tab_click(category, theme_dirs, container, load_image, on_click, grid_cols):
    paths = list_icon(category.lower(), theme_dirs)
    return display_icon(container, paths, load_image, on_click, grid_cols)


