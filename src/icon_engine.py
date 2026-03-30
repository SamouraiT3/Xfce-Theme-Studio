import os

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
        if category not in root.lower():
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


# 🔹 4. Affichage dans Tkinter
import tkinter as tk

def display_icon(container, paths, load_image, on_click, grid_cols=1):
    for child in container.winfo_children():
        child.destroy()

    photo_refs = []
    icon_items = []

    for idx, path in enumerate(paths):
        r, c = divmod(idx, grid_cols)

        cell = tk.Frame(container, width=80, height=90, bg= "#f0f0f0", bd=1, relief=tk.RIDGE)
        cell.grid(row=r, column=c, padx=6, pady=6)
        cell.pack_propagate(False)

        img = load_image(path, (64, 64))

        if img:
            lbl = tk.Label(cell, image=img)
            photo_refs.append(img)
        else:
            lbl = tk.Label(cell, text="X")

        lbl.pack(expand=True)

        lbl.bind(
            "<Button-1>",
            lambda e, p=path, c=cell, i=img: on_click(p, c, i)
        )

        # 🔥 IMPORTANT
        icon_items.append({
            "path": path,
            "cell": cell
        })

    return icon_items, photo_refs


# 🔹 5. Clic onglet
def tab_click(category, theme_dirs, container, load_image, on_click, grid_cols):
    paths = list_icon(category.lower(), theme_dirs)
    return display_icon(container, paths, load_image, on_click, grid_cols)


