import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from pathlib import Path
import cairosvg
from io import BytesIO
from PIL import Image, ImageTk
import subprocess
import os

from icon_engine import tab_click, display_icon
from theme_manage import create_theme_popup, delete_theme_popup, refresh_theme_listbox, on_theme_select, save_theme, reset_theme, USER_PATH, SYSTEM_PATH, list_themes, get_theme_dirs_with_inheritance
from icon_modify import apply_new_icon, refresh_icone_widget, refresh_icon_cell, has_unsaved_changes, changeFalse
from mimetype_tab import refresh_list, items, displayed


# Fenêtre principale
root = tk.Tk()
root.title("Xfce Theme Studio -- Create and customize Icon theme")
root.geometry("975x650")
root.minsize(975, 650)
root.resizable(True, True)

# Fonctions d'action (placeholders)
def action_inactive():
    messagebox.showinfo("Info", "Fonctionnalité non implémentée (interface prototype)")

# Aide au chargement des images avec ou sans Pillow
def load_image(path, size=(64, 64)):
    p = Path(path)
    if not p.exists():
        return None

    try:
        # 🔹 SVG → conversion RAM
        if path.lower().endswith(".svg"):
            png_data = cairosvg.svg2png(url=str(p))
            img = Image.open(BytesIO(png_data))

        # 🔹 PNG / autres
        else:
            img = Image.open(str(p))

        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    except Exception as e:
        print("Erreur image:", path, e)
        return None

# Barre d'action
toolbar = tk.Frame(root, bd=1, relief=tk.RAISED, padx=4, pady=4)
toolbar.pack(fill=tk.X)

btn_new = tk.Button(toolbar, text="New theme", command=lambda: create_theme_popup(root, theme_listbox))
btn_new.pack(side=tk.LEFT, padx=4, pady=2)
btn_delete = tk.Button(toolbar, text="delete theme", command=lambda: delete_theme_popup(root, theme_listbox))
btn_delete.pack(side=tk.LEFT, padx=4, pady=2)
btn_save = tk.Button(toolbar, text="save", command=lambda: save_theme(theme_name))
btn_save.pack(side=tk.LEFT, padx=4, pady=2)
btn_reset = tk.Button(toolbar, text="Reset changes", command=lambda: reset_theme(theme_name))
btn_reset.pack(side=tk.LEFT, padx=4, pady=2)

# Cadre principal
main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

# Liste des thèmes (gauche)
left_frame = tk.LabelFrame(main_frame, text="Custom themes", padx=6, pady=6, width=250)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 4))

theme_listbox = tk.Listbox(left_frame, font=("Arial", 11))
theme_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

list_scroll = tk.Scrollbar(left_frame, orient=tk.VERTICAL, command=theme_listbox.yview)
theme_listbox.config(yscrollcommand=list_scroll.set)
list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

# Zone de details du thème (droite)
right_frame = tk.LabelFrame(main_frame, text="Theme details", padx=6, pady=6)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))

label_name = tk.Label(right_frame, text="Name :", font=("Arial", 12))
label_name.pack(anchor=tk.W, pady=4)
entry_name = tk.Entry(right_frame, font=("Arial", 12), width=50)
entry_name.pack(anchor=tk.W, pady=4)

# Onglets d'icônes par catégorie

GRID_COLS = 6

class IconTab:
    def __init__(self, parent, category, load_image, tab_click, action_inactive):
        self.category = category
        self.load_image = load_image
        self.tab_click = tab_click
        self.action_inactive = action_inactive

        # Onglet
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text=category)

        # Barre de recherche
        self.search_var = tk.StringVar()
        search_holder = tk.Frame(self.frame, padx=6, pady=4)
        search_holder.pack(fill=tk.X)
        tk.Label(search_holder, text="Search :", font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_holder, textvariable=self.search_var, font=("Arial", 11), width=30)
        self.search_entry.pack(side=tk.LEFT, padx=4)

        # Frame principale avec icons + preview
        self.main_frame = tk.Frame(self.frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Frame icônes (canvas scrollable)
        self.content_frame = tk.Frame(self.main_frame, padx=6, pady=6)
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scroll_canvas = tk.Canvas(self.content_frame, highlightthickness=0)
        self.scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = tk.Scrollbar(self.content_frame, orient=tk.VERTICAL, command=self.scroll_canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.icons_container = tk.Frame(self.scroll_canvas)
        self.canvas_window = self.scroll_canvas.create_window((0, 0), window=self.icons_container, anchor="nw")

        # Preview intégré
        self.preview_frame = tk.Frame(self.main_frame)
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_label = tk.Label(self.preview_frame, text="\n\n          Preview          ", font=("Arial", 12, "bold"))
        self.preview_label.pack(pady=(0, 6))
        self.large_preview = tk.Label(self.preview_frame, text="[128x128]", bg="#ddd", relief=tk.SUNKEN)
        self.large_preview.pack(pady=(0, 10))
        self.large_preview_images = {}  # key = nom de l'icône
        self.btn_change_image = tk.Button(self.preview_frame, text="Upload", command=self.on_upload_click)
        self.btn_change_image.pack(pady=6)

        # Variables internes
        self.resize_job = {"id": None}
        self.current_cols = {"value": GRID_COLS}
        self.icon_items = []
        self.icon_photo_refs = []
        self.selected_icon_cell = {"cell": None}
        self.search_items = []
        self.current_theme_name = ""
        self.current_icone_path = ""

        # Bindings
        self.scroll_canvas.bind("<Configure>", lambda e: self.on_resize())        
        self.scroll_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.scroll_canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.scroll_canvas.bind("<Button-5>", self.on_mouse_wheel)
        self.search_var.trace_add("write", self.refresh_icons)

    # Les fonction essentiel à l'affichage des onglets

    def build_icons(self, theme_dirs):
        self.icon_items, self.icon_photo_refs = self.tab_click(
            self.category,
            theme_dirs,
            self.icons_container,
            self.load_image,
            self.on_click,
            GRID_COLS
        )
        self.scroll_canvas.update_idletasks()  # calcule la taille de tous les widgets enfants
        self.scroll_canvas.configure(
            scrollregion=(0, 0, self.icons_container.winfo_width(), self.icons_container.winfo_height()))

    def on_click(self, path, cell, img):
        print("CLICK FROM TAB:", self.category)
        print("CLICK:", path)
        print("CELL:", cell)
        print("IMG:", img)

        self.current_icon_path = path

        self.select_icon(cell, path, img)

    def select_icon(self, cell, icon_id, icon_photo=None):
        # reset ancienne sélection
        try :
            if self.selected_icon_cell["cell"]:
                self.selected_icon_cell["cell"].config(background="#f0f0f0", bd=1, relief=tk.RIDGE)
        except Exception :
            print("j'en bat les couille")
        # nouvelle sélection
        self.selected_icon_cell["cell"] = cell
        cell.config(background="yellow", bd=2, relief=tk.SOLID)

        # texte fallback
        self.large_preview.config(text=Path(icon_id).name, bg="#fff")

        # image preview
        img = self.load_image(icon_id, (128,128))
        if img:
            self.large_preview_images[icon_id] = img  # garde référence
            self.large_preview.config(image=img, text="")
            self.large_preview.image = img  # 🔥 Tkinter nécessite cette ligne
        else:
            self.large_preview.config(image="", text=Path(icon_id).name)

    def on_mouse_wheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.scroll_canvas.yview_scroll(3, "units")
        elif event.num == 4 or event.delta > 0:
            self.scroll_canvas.yview_scroll(-3, "units")

    def on_resize(self, *args):
        """Handler appelé à chaque modification de taille du canvas."""
        # Annule l'ancien timer si l'utilisateur continue de redimensionner
        if self.resize_job["id"]:
            self.scroll_canvas.after_cancel(self.resize_job["id"])

        # Lance un nouveau timer de 120ms
        self.resize_job["id"] = self.scroll_canvas.after(120, self.do_resize)


    def do_resize(self, *args):
        """Exécuté après que le redimensionnement soit terminé."""
        width = self.scroll_canvas.winfo_width()
        cell_size = 92  # largeur d'une cellule
        new_cols = max(1, width // cell_size)

        global GRID_COLS
        if new_cols == self.current_cols["value"]:
            return  # pas besoin de changer

        self.current_cols["value"] = new_cols
        if new_cols != 1:
            GRID_COLS = new_cols

        # Choisir les paths à afficher
        paths = self.search_items if self.search_items else [item["path"] for item in self.icon_items]

        # Rafraîchir les icônes
        new_items, _ = display_icon(
            self.icons_container,
            paths,
            self.load_image,
            self.on_click,
            GRID_COLS
        )

        # Mettre à jour le scrollregion
        self.scroll_canvas.after_idle(lambda: self.scroll_canvas.configure(
            scrollregion=(0, 0, self.icons_container.winfo_width(), self.icons_container.winfo_height())
        ))

        print(f"RESIZE terminé : GRID_COLS={GRID_COLS}")

    def refresh_icons(self, *args):
        query = self.search_var.get().strip().lower()
        self.selected_icon_cell["cell"] = None
        self.search_items.clear()

        for item in self.icon_items:
            name = Path(item["path"]).stem.lower()
            if not query or query in name:
                self.search_items.append(item["path"])

        for child in self.icons_container.winfo_children():
            child.destroy()

        display_icon(
            self.icons_container,
            self.search_items,
            self.load_image,
            self.on_click,
            GRID_COLS
        )
        self.scroll_canvas.after_idle(lambda: self.scroll_canvas.configure(
            scrollregion=(0, 0, self.icons_container.winfo_width(), self.icons_container.winfo_height())
        ))

    def on_upload_click(self):

        zenity_cmd = ['zenity', '--file-selection', '--title=Choose an icon', '--file-filter=Images | *.png *.svg *.xpm']
        result = subprocess.run(zenity_cmd, capture_output=True, text=True)
        chemin_selectionne = result.stdout.strip()


        if chemin_selectionne and self.selected_icon_cell["cell"]:
            theme_name = self.current_theme_name
            # 🔹 nom de l'icône à remplacer
            icone_originale = self.current_icon_path

            print(icone_originale)
            
            dest_path = apply_new_icon(theme_name, self.category, chemin_selectionne, icone_originale)
            if dest_path:
                refresh_icone_widget(self.large_preview, dest_path, load_image)

                # mettre à jour la cellule dans la grille
            if self.selected_icon_cell["cell"]:
                refresh_icon_cell(self.selected_icon_cell["cell"], dest_path, self.load_image)

            self.update_icon_items(str(icone_originale), str(dest_path))

            cell = self.selected_icon_cell["cell"]

            # 🔥 nouveau path
            new_path = str(dest_path)

            # 🔥 rebind du click avec le bon path
            for child in cell.winfo_children():
                child.bind("<Button-1>", lambda e, p=new_path, c=cell: self.on_click(p, c, None))

            cell.bind("<Button-1>", lambda e, p=new_path, c=cell: self.on_click(p, c, None))

    def update_icon_items(self, old_path, new_path):
        """
        Met à jour self.icon_items pour remplacer old_path par new_path.
        Met aussi à jour self.search_items et la cellule sélectionnée si nécessaire.
        """
        # Mettre à jour icon_items
        for item in self.icon_items:
            if item["path"] == old_path:
                item["path"] = new_path
                break

        # Mettre à jour search_items si recherche active
        for i, path in enumerate(self.search_items):
            if path == old_path:
                self.search_items[i] = new_path

        # 🔹 Mettre à jour la cellule sélectionnée
        if self.selected_icon_cell.get("cell") and self.current_icon_path == old_path:
            self.current_icon_path = new_path

# --- Utilisation ---
tab_parent = ttk.Notebook(right_frame)
tab_parent.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

categories = ["Apps", "Actions", "Places", "Status", "Devices", "Emblems"]

tabs = []
for cat in categories:
    tabs.append(IconTab(tab_parent, cat, load_image, tab_click, action_inactive))

# Onglet spécifique Mimetypes
mime_frame = ttk.Frame(tab_parent)
tab_parent.add(mime_frame, text="Mimetypes")

mime_left = tk.Frame(mime_frame, padx=6, pady=6)
mime_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

mime_search_var = tk.StringVar()
mime_search_holder = tk.Frame(mime_left)
mime_search_holder.pack(fill=tk.X, pady=(0, 6))
mdi = tk.Label(mime_search_holder, text="Search :", font=("Arial", 11))
mdi.pack(side=tk.LEFT)
mime_search_entry = tk.Entry(mime_search_holder, textvariable=mime_search_var, font=("Arial", 11), width=30)
mime_search_entry.pack(side=tk.LEFT, padx=4)

mime_list = tk.Listbox(mime_left, font=("Arial", 11))
mime_list.pack(fill=tk.BOTH, expand=True)

# Populate the mimetype list
refresh_list(mime_list, mime_search_var)

def on_mime_select(event):
    if not mime_list.curselection():
        return
    idx = mime_list.curselection()[0]
    item_index = displayed[idx]
    mime, texte = items[item_index]
    mime_info_label.config(text=texte)
    
    # Extract MIME type from texte (first one)
    mime_types = texte.split(": ")[1].split(", ")
    actual_mime = mime_types[0] if mime_types else ""
    print(f"DEBUG: Selected: {mime}, texte: {texte}, actual_mime: {actual_mime}")
    
    # Find and display the MIME icon
    if actual_mime:
        # Try specific name first
        mime_icon_name = actual_mime.replace('/', '-')
        # Then try generic names
        main_type = actual_mime.split('/')[0]
        generic_names = [mime_icon_name, f"{main_type}-x-generic", f"{main_type}-x-generic-symbolic"]
        print(f"DEBUG: Trying names: {generic_names}")
        if theme_name:
            theme_dirs = get_theme_dirs_with_inheritance(theme_name)
        else:
            # Use default theme or first available
            system_themes, custom_themes = list_themes()
            if custom_themes:
                theme_name_default = custom_themes[0]
            elif system_themes:
                theme_name_default = system_themes[0]
            else:
                theme_name_default = None
            if theme_name_default:
                theme_dirs = get_theme_dirs_with_inheritance(theme_name_default)
        
        for theme_dir in theme_dirs:
            # Search in all */mimetypes subdirs
            for root, dirs, files in os.walk(theme_dir):
                if os.path.basename(root) == "mimetypes":
                    for file in files:
                        name, ext = os.path.splitext(file)
                        for try_name in generic_names:
                            if name == try_name and ext.lower() in ['.png', '.svg', '.xpm']:
                                icon_path = os.path.join(root, file)
                                print(f"DEBUG: Found icon: {icon_path}")
                                img = load_image(icon_path, (64, 64))
                                print(f"DEBUG: img: {img}")
                                if img:
                                    print("DEBUG: Setting image")
                                    mime_image_placeholder.config(image=img, text="")
                                    mime_image_placeholder.image = img  # Keep reference
                                    return
    # If not found, show placeholder
    print("DEBUG: No icon found")
    mime_image_placeholder.config(image="", text="[Icon extension]")

mime_right = tk.LabelFrame(mime_frame, text="Extension details", padx=6, pady=6)
mime_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

mime_info_label = tk.Label(mime_right, text="Select an extension on the left", font=("Arial", 11), pady=10)
mime_info_label.pack()

mime_image_placeholder = tk.Label(mime_right, text="[Icon extension]", bg="#ddd", relief=tk.SUNKEN)
mime_image_placeholder.pack(pady=10)

btn_change_mime_icon = tk.Button(mime_right, text="Change", command=action_inactive)
btn_change_mime_icon.pack()

mime_list.bind('<ButtonRelease-1>', on_mime_select)
mime_search_var.trace_add('write', lambda name, index, mode: refresh_list(mime_list, mime_search_var))


# Barre du bas
bottom_bar = tk.Frame(root, bd=1, relief=tk.SUNKEN, padx=6, pady=6)
bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)

btn_import = tk.Button(bottom_bar, text="Import Theme", command=action_inactive)
btn_import.pack(side=tk.RIGHT, padx=4)
btn_export = tk.Button(bottom_bar, text="Export Theme", command=action_inactive)
btn_export.pack(side=tk.RIGHT, padx=4)
btn_help = tk.Button(bottom_bar, text="Help", command=action_inactive)
btn_help.pack(side=tk.RIGHT, padx=4)

# popup de sauvegarde

def ask_unsaved_changes(root):
    popup = tk.Toplevel(root)
    popup.title("Unsaved changes")
    popup.geometry("300x150")
    popup.transient(root)

    popup.update_idletasks()
    popup.deiconify()
    popup.grab_set()

    tk.Label(popup, text="You have unsaved changes.\nWhat do you want to do ?").pack(pady=15)

    result = {"choice": None}

    def save():
        result["choice"] = "save"
        popup.destroy()

    def reset():
        result["choice"] = "reset"
        popup.destroy()

    def cancel():
        result["choice"] = "cancel"
        popup.destroy()

    btn_frame = tk.Frame(popup)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="Save", command=save, bg="#28a745", fg="white").pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Reset changes", command=reset, bg="#dc3545", fg="white").pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Cancel", command=cancel, bg="#555555", fg="white").pack(side=tk.LEFT, padx=5)

    root.wait_window(popup)
    return result["choice"]

def on_theme_change(event):
    global theme_name
    print(theme_name)
    if has_unsaved_changes():
        choice = ask_unsaved_changes(root)

        if choice == "cancel":
            return  # bloque

        elif choice == "save":
            save_theme(theme_name)

        elif choice == "reset":
            reset_theme(theme_name)
    # continuer normalement
    changeFalse()
    theme_name = theme_listbox.get(theme_listbox.curselection())
    print(theme_name)
    on_theme_select(event, theme_listbox, tabs, entry_name)

theme_name = ""
refresh_theme_listbox(theme_listbox)
theme_listbox.bind("<<ListboxSelect>>", on_theme_change)

def on_close():
    if has_unsaved_changes():
        choice = ask_unsaved_changes(root)

        if choice == "cancel":
            return

        elif choice == "save":
            save_theme(theme_name)

        elif choice == "reset":
            reset_theme(theme_name)

    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
