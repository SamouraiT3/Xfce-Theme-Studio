import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio
from pathlib import Path
import cairosvg
from io import BytesIO
from PIL import Image
import subprocess
import os
import shutil
import tarfile
import webbrowser

from icon_engine import tab_click, display_icon, best_icon
from theme_manage import create_theme_popup, delete_theme_popup, refresh_theme_listbox, on_theme_select, save_theme, reset_theme, USER_PATH, SYSTEM_PATH, list_themes, get_theme_dirs_with_inheritance, rename_theme, find_theme_path
from icon_modify import apply_new_icon, refresh_icone_widget, refresh_icon_cell, has_unsaved_changes, changeFalse
from mimetype_tab import refresh_list, items, displayed

# Fenêtre principale
root = Gtk.Window()
root.set_title("Xfce Theme Studio -- Create and customize Icon theme")
root.set_default_size(975, 650)
root.set_resizable(True)

# CSS pour le surlignage des icônes sélectionnées
css_provider = Gtk.CssProvider()
css_provider.load_from_data(b"""
    .icon-cell-selected {
        border: 2px solid #0078d4;
        border-radius: 6px;
        background-color: rgba(0, 120, 212, 0.12);
    }
""")
Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

# Fonctions d'action (placeholders)
def action_inactive():
    dialog = Gtk.MessageDialog(root, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, "Fonctionnalité non implémentée (interface prototype)")
    dialog.run()
    dialog.destroy()

def show_help():
    win = Gtk.Window()
    win.set_title("Help")
    win.set_default_size(400, 270)
    win.set_resizable(False)
    win.set_transient_for(root)
    win.set_modal(True)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.set_margin_top(10)
    box.set_margin_bottom(10)
    box.set_margin_start(10)
    box.set_margin_end(10)
    win.add(box)

    label = Gtk.Label()
    label.set_markup("<b>Need help or found a bug?</b>")
    box.pack_start(label, False, False, 10)

    # Fonction pour ouvrir les liens
    def open_link(url):
        webbrowser.open(url)

    # GitHub
    github = "https://github.com/SamouraiT3/Xfce-Theme-Studio"
    label_gh = Gtk.Label(label="GitHub:")
    label_gh.set_alignment(0, 0.5)
    box.pack_start(label_gh, False, False, 2)
    
    entry_gh = Gtk.Entry()
    entry_gh.set_text(github)
    entry_gh.set_sensitive(False)
    box.pack_start(entry_gh, False, False, 2)
    
    btn_gh = Gtk.Button(label="Open")
    btn_gh.connect("clicked", lambda *args: open_link(github))
    box.pack_start(btn_gh, False, False, 2)

    # Issues
    issues = "https://github.com/SamouraiT3/Xfce-Theme-Studio/issues"
    label_iss = Gtk.Label(label="Issues:")
    label_iss.set_alignment(0, 0.5)
    box.pack_start(label_iss, False, False, 2)
    
    entry_iss = Gtk.Entry()
    entry_iss.set_text(issues)
    entry_iss.set_sensitive(False)
    box.pack_start(entry_iss, False, False, 2)
    
    btn_iss = Gtk.Button(label="Open")
    btn_iss.connect("clicked", lambda *args: open_link(issues))
    box.pack_start(btn_iss, False, False, 2)

    # Email
    email = "samourai.t3@gmail.com"
    label_email = Gtk.Label(label="Contact:")
    label_email.set_alignment(0, 0.5)
    box.pack_start(label_email, False, False, 2)
    
    entry_email = Gtk.Entry()
    entry_email.set_text(email)
    entry_email.set_sensitive(False)
    box.pack_start(entry_email, False, False, 2)

    win.show_all()

def messagebox_showinfo(title, message):
    dialog = Gtk.MessageDialog(root, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, message)
    dialog.set_title(title)
    dialog.run()
    dialog.destroy()

def messagebox_showerror(title, message):
    dialog = Gtk.MessageDialog(root, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, message)
    dialog.set_title(title)
    dialog.run()
    dialog.destroy()

def messagebox_askyesno(title, message):
    dialog = Gtk.MessageDialog(root, 0, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO, message)
    dialog.set_title(title)
    response = dialog.run()
    dialog.destroy()
    return response == Gtk.ResponseType.YES

def import_theme():
    zenity_cmd = ['zenity', '--file-selection', '--title=Import Theme', '--file-filter=Themes | *.tar.gz *.zip']
    env = os.environ.copy()
    env['DISPLAY'] = os.environ.get('DISPLAY', ':0')
    
    try:
        process = subprocess.Popen(zenity_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        stdout, stderr = process.communicate(timeout=30)
        selected_path = stdout.strip()
    except subprocess.TimeoutExpired:
        process.kill()
        messagebox_showerror("Error", "Import cancelled or timed out")
        return
    
    if not selected_path:
        return

    # Determine if it's a file or directory
    if os.path.isfile(selected_path):
        # Handle archive import
        if selected_path.lower().endswith(('.tar.gz', '.tgz', '.zip')):
            # Extract archive to temp directory first
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                extract_dir = os.path.join(temp_dir, "extracted")
                os.makedirs(extract_dir)
                
                try:
                    if selected_path.lower().endswith('.zip'):
                        import zipfile
                        with zipfile.ZipFile(selected_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                    else:
                        with tarfile.open(selected_path, 'r:gz') as tar_ref:
                            tar_ref.extractall(extract_dir)
                    
                    # Find the theme directory (should be the only directory in extract_dir)
                    extracted_items = os.listdir(extract_dir)
                    if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                        theme_source_dir = os.path.join(extract_dir, extracted_items[0])
                        theme_name = extracted_items[0]
                    else:
                        # Multiple items or files, use the archive name without extension
                        theme_name = os.path.splitext(os.path.splitext(os.path.basename(selected_path))[0])[0]
                        theme_source_dir = extract_dir
                    
                    # Copy to user themes
                    system, custom = list_themes()
                    dest = os.path.join(USER_PATH, theme_name)
                    
                    if theme_name in system or theme_name in custom:
                        overwrite = messagebox_askyesno(
                            "Overwrite theme?",
                            f"The theme '{theme_name}' already exists. Overwrite?"
                        )
                        if not overwrite:
                            return
                        shutil.rmtree(dest, ignore_errors=True)
                    
                    shutil.copytree(theme_source_dir, dest, dirs_exist_ok=True)
                    messagebox_showinfo("Success", f"Theme '{theme_name}' imported from archive")
                    refresh_theme_listbox(theme_listbox)
                    
                except Exception as e:
                    messagebox_showerror("Error", f"Failed to extract archive: {e}")
        else:
            messagebox_showerror("Error", "Unsupported file format. Please select a .tar.gz, .zip file or a theme directory.")
    else:
        # Handle directory import (existing code)
        theme_name = os.path.basename(os.path.normpath(selected_path))
        system, custom = list_themes()
        dest = os.path.join(USER_PATH, theme_name)

        if theme_name in system or theme_name in custom:
            overwrite = messagebox_askyesno(
                "Overwrite theme?",
                f"The theme '{theme_name}' already exists. Overwrite?"
            )
            if not overwrite:
                return
            shutil.rmtree(dest, ignore_errors=True)

        try:
            shutil.copytree(selected_path, dest, dirs_exist_ok=True)
            messagebox_showinfo("Success", f"Theme '{theme_name}' imported")
            refresh_theme_listbox(theme_listbox)
        except Exception as e:
            messagebox_showerror("Error", f"Import failed: {e}")

def export_theme():
    global theme_name
    if not theme_name:
        messagebox_showerror("Error", "Select a theme first")
        return

    source_dir = find_theme_path(theme_name)
    if not source_dir or not os.path.isdir(source_dir):
        messagebox_showerror("Error", "Theme folder not found")
        return

    zenity_cmd = ['zenity', '--file-selection', '--save', '--title=Export Theme', '--filename=' + f"{theme_name}.tar.gz"]
    result = subprocess.run(zenity_cmd, capture_output=True, text=True)
    target_file = result.stdout.strip()
    
    if not target_file:
        return

    # Add .tar.gz extension if not present
    if not target_file.lower().endswith(('.tar.gz', '.tgz')):
        target_file += '.tar.gz'

    try:
        with tarfile.open(target_file, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))
        messagebox_showinfo("Success", f"Theme exported to {target_file}")
    except Exception as e:
        messagebox_showerror("Error", f"Export failed: {e}")

def rename_theme_entry(event=None):
    global theme_name
    if not theme_name:
        return

    new_name = entry_name.get_text().strip()
    if not new_name:
        messagebox_showerror("Error", "Theme name cannot be empty")
        entry_name.set_text(theme_name)
        return

    if new_name == theme_name:
        return

    success, error = rename_theme(theme_name, new_name)
    if not success:
        messagebox_showerror("Error", error)
        entry_name.set_text(theme_name)
        return

    messagebox_showinfo("Success", f"Theme renamed to {new_name}")
    
    # Obtenir le thème actuel du système
    try:
        result = subprocess.run(['xfconf-query', '-c', 'xsettings', '-p', '/Net/IconThemeName'], 
                              capture_output=True, text=True)
        current_system_theme = result.stdout.strip() if result.returncode == 0 else None
        
        # Si le thème renommé est le thème actif du système, le mettre à jour
        if current_system_theme == theme_name:
            subprocess.run(['xfconf-query', '-c', 'xsettings', '-p', '/Net/IconThemeName', '-s', new_name],
                         capture_output=True)
    except Exception as e:
        print(f"Could not update system theme: {e}")
    
    theme_name = new_name
    refresh_theme_listbox(theme_listbox)

    # Re-sélectionner le thème renommé
    model = theme_listbox.get_model()
    for i, row in enumerate(model):
        if row[0] == theme_name:
            theme_listbox.set_cursor(i, None)
            on_theme_select(None, theme_listbox, tabs, entry_name)
            break

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

        # 🔹 XPM → conversion temporaire avec ImageMagick
        elif path.lower().endswith(".xpm"):
            import tempfile
            import subprocess
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                subprocess.run(["convert", str(p), tmp_path], check=True, capture_output=True)
                img = Image.open(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        # 🔹 PNG / autres
        else:
            img = Image.open(str(p))

        img = img.resize(size, Image.LANCZOS)
        
        # Convertir via PNG en mémoire → GdkPixbuf copie les données (évite le bug GC de new_from_data)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        loader.write(buf.read())
        loader.close()
        pixbuf = loader.get_pixbuf()
        
        return pixbuf

    except Exception as e:
        print("Erreur image:", path, e)
        return None


def find_same_icon_paths(filename, exclude_theme=None):
    """Retourne une meilleure résolution par thème pour les images portant le même nom, sans tenir compte de l'extension."""
    target_name = Path(filename).stem
    theme_matches = []
    for base_path, category in [(USER_PATH, "Custom"), (SYSTEM_PATH, "System")]:
        if not os.path.isdir(base_path):
            continue

        for theme in sorted(os.listdir(base_path)):
            theme_dir = os.path.join(base_path, theme)
            if not os.path.isdir(theme_dir):
                continue
            if not os.path.isfile(os.path.join(theme_dir, "index.theme")):
                continue
            if exclude_theme and theme == exclude_theme:
                continue

            candidates = []
            for root_dir, dirs, files in os.walk(theme_dir):
                for file in files:
                    if Path(file).stem == target_name:
                        candidates.append(os.path.join(root_dir, file))

            if not candidates:
                continue

            best_path = best_icon(candidates)
            if not best_path:
                continue

            theme_matches.append({
                "theme": theme,
                "source": category,
                "path": best_path,
                "relative": os.path.relpath(best_path, theme_dir),
            })

    return sorted(theme_matches, key=lambda item: (item["theme"].lower(), item["source"]))


def create_same_icon_popup(current_icon_path, current_theme_name, category="apps", on_icon_selected=None):
    icon_name = Path(current_icon_path).name
    matches = find_same_icon_paths(icon_name, exclude_theme=current_theme_name)

    if not matches:
        messagebox_showinfo("Browse themes", f"Aucune icône '{icon_name}' trouvée dans les autres thèmes.")
        return

    popup = Gtk.Window()
    popup.set_title(f"Browse themes — {icon_name}")
    popup.set_default_size(650, 420)
    popup.set_transient_for(root)
    popup.set_modal(True)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.set_margin_start(8)
    box.set_margin_end(8)
    box.set_margin_top(8)
    box.set_margin_bottom(8)
    popup.add(box)

    # Search bar
    search_box = Gtk.Box(spacing=6)
    box.pack_start(search_box, False, False, 0)
    
    lbl_search = Gtk.Label(label="Search theme:")
    search_box.pack_start(lbl_search, False, False, 0)
    
    search_entry = Gtk.Entry()
    search_entry.set_width_chars(35)
    search_box.pack_start(search_entry, True, True, 0)

    # ScrollView with Grid
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    box.pack_start(scrolled, True, True, 0)

    grid = Gtk.Grid()
    grid.set_row_spacing(6)
    grid.set_column_spacing(6)
    scrolled.add(grid)

    visible_matches = []
    selected_item = {"item": None}
    selected_widget = {"widget": None}

    def select_item(item, widget):
        if selected_widget["widget"]:
            old_widget = selected_widget["widget"]
            old_widget.set_state_flags(Gtk.StateFlags.NORMAL, True)
            old_widget.get_style_context().remove_class("icon-cell-selected")
        selected_item["item"] = item
        selected_widget["widget"] = widget
        widget.set_state_flags(Gtk.StateFlags.SELECTED, True)
        widget.get_style_context().add_class("icon-cell-selected")

    def refresh_grid(*args):
        selected_item["item"] = None
        selected_widget["widget"] = None
        query = search_entry.get_text().strip().lower()
        
        # Clear grid
        children = []
        grid.foreach(children.append)
        for child in children:
            grid.remove(child)

        visible_matches.clear()
        columns = 4
        row = 0
        col = 0

        for item in matches:
            if query and query not in item["theme"].lower() and query not in item["relative"].lower():
                continue
            visible_matches.append(item)

            cell = Gtk.Frame()
            cell.set_shadow_type(Gtk.ShadowType.IN)
            cell.set_margin_start(6)
            cell.set_margin_end(6)
            cell.set_margin_top(6)
            cell.set_margin_bottom(6)
            
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin=8)
            cell.add(vbox)

            wrapper = Gtk.EventBox()
            wrapper.add(cell)
            wrapper.set_visible_window(False)
            grid.attach(wrapper, col, row, 1, 1)

            icon_img = load_image(item["path"], (64, 64))
            if icon_img:
                icon_img = icon_img.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)
                img = Gtk.Image.new_from_pixbuf(icon_img)
            else:
                img = Gtk.Label(label=Path(item["path"]).name)
            vbox.pack_start(img, False, False, 4)

            theme_label = Gtk.Label(label=item["theme"])
            theme_label.set_line_wrap(True)
            theme_label.set_width_chars(15)
            vbox.pack_start(theme_label, False, False, 4)

            def make_callback(selected=item, widget=cell):
                return lambda *args: select_item(selected, widget)

            wrapper.connect("button-press-event", make_callback())

            col += 1
            if col >= columns:
                col = 0
                row += 1

        grid.show_all()

    def use_selected_icon():
        if not selected_item["item"]:
            messagebox_showerror("Error", "Select an icon first")
            return
        
        # Copy the selected icon to the temp theme folder
        try:
            source_path = selected_item["item"]["path"]
            
            # Obtenir le répertoire temporaire du thème actuel
            temp_path = Path.home() / ".xfce-theme-studio" / "theme" / f"{current_theme_name}.temp"
            dest_dir = temp_path / category.lower()  # Utiliser la catégorie passée
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Obtenir le nom du fichier à remplacer
            dest_filename = Path(current_icon_path).name
            dest_full_path = dest_dir / dest_filename
            
            # Copier le fichier
            shutil.copy(source_path, dest_full_path)
            
            # Marquer comme modifié
            import icon_modify
            icon_modify.modifications_en_cours = True
            
            messagebox_showinfo("Success", f"Icon copied: {dest_filename}")
            if on_icon_selected:
                on_icon_selected(str(dest_full_path))
            popup.destroy()
        except Exception as e:
            messagebox_showerror("Error", f"Failed to copy icon: {e}")

    def download_selected_icon():
        if not selected_item["item"]:
            messagebox_showerror("Error", "Select an icon first")
            return
        try:
            source_path = selected_item["item"]["path"]
            theme_prefix = selected_item["item"]["theme"]
            downloads_dir = subprocess.check_output(["xdg-user-dir", "DOWNLOAD"]).decode().strip()
            filename = f"{theme_prefix}_{Path(source_path).name}"
            dest = os.path.join(os.path.expanduser("~"), downloads_dir, filename)
            shutil.copy(source_path, dest)
            messagebox_showinfo("Succès", f"Icône copiée dans :\n{dest}")
        except Exception as e:
            messagebox_showerror("Erreur", f"Impossible de copier le fichier:\n{e}")

    search_entry.connect("changed", refresh_grid)
    refresh_grid()

    btn_box = Gtk.Box(spacing=6)
    box.pack_start(btn_box, False, False, 0)

    btn_use = Gtk.Button(label="Use this icon")
    btn_use.connect("clicked", lambda *args: use_selected_icon())
    btn_box.pack_start(btn_use, False, False, 0)

    btn_download = Gtk.Button(label="Download icon")
    btn_download.connect("clicked", lambda *args: download_selected_icon())
    btn_box.pack_start(btn_download, False, False, 0)

    btn_close = Gtk.Button(label="Close")
    btn_close.connect("clicked", lambda *args: popup.destroy())
    btn_box.pack_end(btn_close, False, False, 0)

    popup.show_all()

# Barre d'action avec boutons de fenêtre
toolbar = Gtk.HeaderBar()
toolbar.set_show_close_button(True)
toolbar.set_title("| Xfce Theme Studio -- Create and customize Icon theme |")
root.set_titlebar(toolbar)

btn_new = Gtk.Button(label="New theme")
btn_new.connect("clicked", lambda *args: create_theme_popup(root, theme_listbox))
toolbar.pack_start(btn_new)

btn_delete = Gtk.Button(label="delete theme")
btn_delete.connect("clicked", lambda *args: delete_theme_popup(root, theme_listbox))
toolbar.pack_start(btn_delete)

btn_save = Gtk.Button(label="save")
btn_save.connect("clicked", lambda *args: save_theme(theme_name))
toolbar.pack_start(btn_save)

btn_reset = Gtk.Button(label="Reset changes")
btn_reset.connect("clicked", lambda *args: reset_theme(theme_name))
toolbar.pack_start(btn_reset)

# Wrapper vertical : contient main_frame (horizontal) + bottom_bar
root_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
root.add(root_vbox)

# Cadre principal (horizontal)
main_frame = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
main_frame.set_margin_start(8)
main_frame.set_margin_end(8)
main_frame.set_margin_top(8)
main_frame.set_margin_bottom(0)
root_vbox.pack_start(main_frame, True, True, 0)

# Liste des thèmes (gauche)
left_frame = Gtk.Frame()
left_frame.set_label("Custom themes")
main_frame.pack_start(left_frame, False, False, 0)
left_frame.set_size_request(250, -1)

left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
left_box.set_margin_start(6)
left_box.set_margin_end(6)
left_box.set_margin_top(6)
left_box.set_margin_bottom(6)
left_frame.add(left_box)

# Create TreeView for themes
theme_store = Gtk.ListStore(str)
theme_listbox = Gtk.TreeView(model=theme_store)
theme_listbox.set_headers_visible(False)

renderer = Gtk.CellRendererText()
column = Gtk.TreeViewColumn("Theme", renderer, text=0)
theme_listbox.append_column(column)

scrolled_themes = Gtk.ScrolledWindow()
scrolled_themes.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
scrolled_themes.add(theme_listbox)
left_box.pack_start(scrolled_themes, True, True, 0)

# Zone de details du thème (droite)
right_frame = Gtk.Frame()
right_frame.set_label("Theme details")
main_frame.pack_end(right_frame, True, True, 0)
right_frame.set_margin_start(4)

right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=6)
right_frame.add(right_box)

label_name = Gtk.Label(label="Name :")
label_name.set_alignment(0, 0.5)
right_box.pack_start(label_name, False, False, 4)

entry_name = Gtk.Entry()
entry_name.set_width_chars(50)
entry_name.connect("activate", rename_theme_entry)
right_box.pack_start(entry_name, False, False, 4)

help_label = Gtk.Label(label="Appuie sur Entrée pour renommer le thème sélectionné.")
help_label.set_alignment(0, 0.5)
help_label.set_opacity(0.7)
right_box.pack_start(help_label, False, False, 6)

# Onglets d'icônes par catégorie

GRID_COLS = 6

class IconTab:
    def __init__(self, parent, category, load_image, tab_click, action_inactive):
        self.category = category
        self.load_image = load_image
        self.tab_click = tab_click
        self.action_inactive = action_inactive

        # Onglet
        self.frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.frame.set_margin_start(6)
        self.frame.set_margin_end(6)
        self.frame.set_margin_top(6)
        self.frame.set_margin_bottom(6)
        parent.append_page(self.frame, Gtk.Label(label=category))

        # Barre de recherche
        search_holder = Gtk.Box(spacing=6)
        search_holder.set_margin_bottom(4)
        self.frame.pack_start(search_holder, False, False, 0)
        
        lbl_search = Gtk.Label(label="Search :")
        search_holder.pack_start(lbl_search, False, False, 0)
        
        self.search_var = Gtk.Entry()
        self.search_var.set_width_chars(30)
        search_holder.pack_start(self.search_var, False, False, 4)

        # Frame principale avec icons + preview
        self.main_frame = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.frame.pack_start(self.main_frame, True, True, 0)

        # Frame icônes (scrolled window)
        self.content_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.content_frame.set_margin_end(6)
        
        self.main_frame.pack_start(self.content_frame, True, True, 0)

        self.scroll_canvas = Gtk.ScrolledWindow()
        self.scroll_canvas.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.content_frame.pack_start(self.scroll_canvas, True, True, 0)

        self.icons_container = Gtk.Grid()
        self.icons_container.set_row_spacing(6)
        self.icons_container.set_column_spacing(6)
        self.scroll_canvas.add(self.icons_container)

        # Preview intégré
        self.preview_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.preview_frame.set_margin_start(6)
        self.main_frame.pack_end(self.preview_frame, False, False, 0)

        self.preview_label = Gtk.Label(label="          Preview          ")
        self.preview_label.set_alignment(0.5, 0.5)
        self.preview_frame.pack_start(self.preview_label, False, False, 6)

        self.large_preview = Gtk.Image()
        self.large_preview.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        self.large_preview.set_pixel_size(128)
        self.large_preview.set_size_request(128, 128)
        self.preview_frame.pack_start(self.large_preview, False, False, 10)

        self.large_preview_images = {}  # key = nom de l'icône

        self.btn_change_image = Gtk.Button(label="Upload")
        self.btn_change_image.connect("clicked", lambda *args: self.on_upload_click())
        self.preview_frame.pack_start(self.btn_change_image, False, False, 6)

        self.btn_browse_in_theme = Gtk.Button(label="Browse themes")
        self.btn_browse_in_theme.connect("clicked", lambda *args: self.browse_same_icons())
        self.preview_frame.pack_start(self.btn_browse_in_theme, False, False, 0)

        self.btn_download_icon = Gtk.Button(label="Download icon")
        self.btn_download_icon.connect("clicked", lambda *args: self.download_icon())
        self.preview_frame.pack_start(self.btn_download_icon, False, False, 6)

        # Variables internes
        self.resize_job = {"id": None}
        self.current_cols = {"value": GRID_COLS}
        self.icon_items = []
        self.icon_photo_refs = []
        self.selected_icon_cell = {"cell": None}
        self.search_items = []
        self.current_theme_name = ""
        self.current_icon_path = ""

        # Bindings
        self.search_var.connect("changed", self.refresh_icons)
        self.scroll_canvas.connect("size-allocate", self.on_resize)

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

    def on_click(self, path, cell, img):

        self.current_icon_path = path

        self.select_icon(cell, path, img)

    def select_icon(self, cell, icon_id, icon_photo=None):
        # reset ancienne sélection
        if self.selected_icon_cell["cell"]:
            old_cell = self.selected_icon_cell["cell"]
            old_cell.set_state_flags(Gtk.StateFlags.NORMAL, True)
            old_cell.get_style_context().remove_class("icon-cell-selected")
        
        # nouvelle sélection
        self.selected_icon_cell["cell"] = cell
        cell.set_state_flags(Gtk.StateFlags.SELECTED, True)
        cell.get_style_context().add_class("icon-cell-selected")

        
        # image preview
        img = self.load_image(icon_id, (128, 128))
        if img:
            img = img.scale_simple(128, 128, GdkPixbuf.InterpType.BILINEAR)
            self.large_preview_images[icon_id] = img
            self.large_preview.set_from_pixbuf(img)
        else:
            self.large_preview.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)

    def on_resize(self, *args):
        """Handler appelé à chaque modification de taille du canvas."""
        width = self.scroll_canvas.get_allocated_width()
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

        print(f"RESIZE terminé : GRID_COLS={GRID_COLS}")

    def refresh_icons(self, *args):
        query = self.search_var.get_text().strip().lower()
        self.selected_icon_cell["cell"] = None
        self.search_items.clear()

        for item in self.icon_items:
            name = Path(item["path"]).stem.lower()
            if not query or query in name:
                self.search_items.append(item["path"])

        # Clear grid (Gtk.Grid n'a pas get_child, on utilise foreach)
        children = []
        self.icons_container.foreach(children.append)
        for child in children:
            self.icons_container.remove(child)

        display_icon(
            self.icons_container,
            self.search_items,
            self.load_image,
            self.on_click,
            GRID_COLS
        )

    def on_upload_click(self):
        zenity_cmd = ['zenity', '--file-selection', '--title=Choose an icon', '--file-filter=Images | *.png *.svg *.xpm']
        result = subprocess.run(zenity_cmd, capture_output=True, text=True)
        chemin_selectionne = result.stdout.strip()

        if chemin_selectionne and self.selected_icon_cell["cell"]:
            theme_name = self.current_theme_name
            # 🔹 nom de l'icône à remplacer
            icone_originale = self.current_icon_path
            
            dest_path = apply_new_icon(theme_name, self.category, chemin_selectionne, icone_originale)
            if dest_path:
                refresh_icone_widget(self.large_preview, dest_path, self.load_image)

                # mettre à jour la cellule dans la grille
            if self.selected_icon_cell["cell"]:
                refresh_icon_cell(self.selected_icon_cell["cell"], dest_path, self.load_image)

            self.update_icon_items(str(icone_originale), str(dest_path))

            cell = self.selected_icon_cell["cell"]
            new_path = str(dest_path)

            for item in self.icon_items:
                if item.get("cell") is cell:
                    if item.get("handler_id") is not None:
                        try:
                            cell.disconnect(item["handler_id"])
                        except Exception:
                            pass
                    item["handler_id"] = cell.connect(
                        "button-press-event",
                        lambda widget, event, p=new_path, c=cell: self.on_click(p, c, None)
                    )
                    item["path"] = new_path
                    break

    def browse_same_icons(self):
        if not self.current_theme_name:
            messagebox_showerror("Error", "Select a theme first")
            return
        if not self.current_icon_path:
            messagebox_showerror("Error", "Select an icon first")
            return

        create_same_icon_popup(
            self.current_icon_path,
            self.current_theme_name,
            self.category,
            on_icon_selected=self.on_browse_icon_replaced
        )

    def on_browse_icon_replaced(self, new_path):
        old_path = self.current_icon_path
        self.current_icon_path = new_path

        # Mettre à jour la grille et l'aperçu immédiatement
        if self.selected_icon_cell["cell"]:
            refresh_icon_cell(self.selected_icon_cell["cell"], new_path, self.load_image)
            refresh_icone_widget(self.large_preview, new_path, self.load_image)

            # Réassigner le handler click pour pointer vers le nouveau chemin
            for item in self.icon_items:
                if item.get("cell") is self.selected_icon_cell["cell"]:
                    if item.get("handler_id") is not None:
                        try:
                            item["cell"].disconnect(item["handler_id"])
                        except Exception:
                            pass
                    item["handler_id"] = item["cell"].connect(
                        "button-press-event",
                        lambda widget, event, p=new_path, c=self.selected_icon_cell["cell"]: self.on_click(p, c, None)
                    )
                    item["path"] = new_path
                    break

        self.update_icon_items(str(old_path), str(new_path))

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

    def download_icon(self):
        if not self.current_theme_name:
            messagebox_showerror("Error", "Select a theme and an icon first")
            return
        
        if not self.current_icon_path:
            messagebox_showerror("Error", "Select an icon first")
            return

        try:
            source = self.current_icon_path

            downloads_dir = subprocess.check_output(["xdg-user-dir", "DOWNLOAD"]).decode().strip()
        
            # Nom du fichier original
            filename = self.current_theme_name + "_" + Path(source).name
            dest = os.path.join(os.path.expanduser("~"), downloads_dir, filename)

            print(f"Copying from {source} to {dest}")
            print(filename)
            

            shutil.copy(source, dest)

            messagebox_showinfo("Succès", f"Icône copiée dans :\n{dest}")

        except Exception as e:
            messagebox_showerror("Erreur", f"Impossible de copier le fichier:\n{e}")

# --- Utilisation ---
tab_parent = Gtk.Notebook()
right_box.pack_start(tab_parent, True, True, 0)

categories = ["Apps", "Actions", "Places", "Status", "Devices", "Emblems"]

tabs = []
for cat in categories:
    tabs.append(IconTab(tab_parent, cat, load_image, tab_click, action_inactive))

# Onglet spécifique Mimetypes
mime_frame = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
mime_frame.set_margin_start(6)
mime_frame.set_margin_end(6)
mime_frame.set_margin_top(6)
mime_frame.set_margin_bottom(6)
tab_parent.append_page(mime_frame, Gtk.Label(label="Mimetypes"))

mime_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
mime_left.set_margin_end(6)
mime_frame.pack_start(mime_left, True, True, 0)

mime_search_holder = Gtk.Box(spacing=6)
mime_search_holder.set_margin_bottom(6)
mime_left.pack_start(mime_search_holder, False, False, 0)

mdi = Gtk.Label(label="Search :")
mime_search_holder.pack_start(mdi, False, False, 0)

mime_search_var = Gtk.Entry()
mime_search_var.set_width_chars(30)
mime_search_holder.pack_start(mime_search_var, False, False, 4)

# Mimetype list
mime_store = Gtk.ListStore(str)
mime_list = Gtk.TreeView(model=mime_store)
mime_list.set_headers_visible(False)

renderer_mime = Gtk.CellRendererText()
column_mime = Gtk.TreeViewColumn("Mimetype", renderer_mime, text=0)
mime_list.append_column(column_mime)

scrolled_mime = Gtk.ScrolledWindow()
scrolled_mime.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
scrolled_mime.add(mime_list)
mime_left.pack_start(scrolled_mime, True, True, 0)

# Populate the mimetype list
refresh_list(mime_list, mime_search_var)

current_mime_icon_path = ""
current_mime_name = ""


def find_mimetype_icon(theme_dir, names):
    matched = []
    for root, dirs, files in os.walk(theme_dir):
        if "/mimetypes" not in root and not root.endswith("mimetypes"):
            continue
        for file in files:
            name, ext = os.path.splitext(file)
            if ext.lower() in ['.png', '.svg', '.xpm'] and name in names:
                matched.append(os.path.join(root, file))

    if not matched:
        return None

    best = None
    best_size = -1
    svg = None
    for path in matched:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".svg":
            svg = path
            continue

        size = 0
        for part in path.split(os.sep):
            if "x" in part and part.split("x")[0].isdigit():
                size = int(part.split("x")[0])
                break
        if size > best_size:
            best_size = size
            best = path

    return best if best else svg


def on_mime_select(event):
    global current_mime_icon_path, current_mime_name, theme_name
    selection = mime_list.get_selection()
    if not selection:
        return
    model, treeiter = selection.get_selected()
    if not treeiter:
        return
    
    idx = model.get_path(treeiter).get_indices()[0]
    item_index = displayed[idx]
    mime, texte = items[item_index]
    mime_info_label.set_text(texte)
    
    # Extract MIME type from texte (first one)
    mime_types = texte.split(": ")[1].split(", ")
    actual_mime = mime_types[0] if mime_types else ""
    
    current_mime_icon_path = ""
    current_mime_name = ""
    
    # Find and display the MIME icon
    if actual_mime:
        mime_icon_name = actual_mime.replace('/', '-')
        current_mime_name = mime_icon_name
        main_type, sub_type = actual_mime.split('/', 1)
        # First, try to find the specific MIME icon
        try_names = [mime_icon_name]
        
        system_themes, custom_themes = list_themes()
        if theme_name:
            theme_dirs = get_theme_dirs_with_inheritance(theme_name)
        else:
            # Use default theme or first available
            if custom_themes:
                theme_name_default = custom_themes[0]
            elif system_themes:
                theme_name_default = system_themes[0]
            else:
                theme_name_default = None
            if theme_name_default:
                theme_dirs = get_theme_dirs_with_inheritance(theme_name_default)

        # Search for the exact MIME icon in theme precedence order
        icon_path = None
        for theme_dir in theme_dirs:
            found = find_mimetype_icon(theme_dir, try_names)
            if found:
                icon_path = found
                
                break

        if icon_path:
            img = load_image(icon_path, (64, 64))
            if img:
                img = img.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)
                mime_image_placeholder.set_from_pixbuf(img)
                current_mime_icon_path = icon_path
                return
        
        # If no specific icon found, try generic names
        generic_names = [f"{main_type}-x-{sub_type}", f"{main_type}-x-generic", f"{main_type}-x-generic-symbolic"]
        # Remove duplicates
        generic_names = list(dict.fromkeys(generic_names))
        
        icon_path = None
        # Chercher d'abord dans le thème actuel et son héritage
        for theme_dir in theme_dirs:
            found = find_mimetype_icon(theme_dir, generic_names)
            if found:
                icon_path = found
                break

        # Si pas trouvé, chercher ensuite dans tous les thèmes installés
        if not icon_path:
            for candidate_theme in custom_themes + system_themes:
                theme_group = get_theme_dirs_with_inheritance(candidate_theme)
                for theme_dir in theme_group:
                    found = find_mimetype_icon(theme_dir, generic_names)
                    if found:
                        icon_path = found
                        break
                if icon_path:
                    break

        if icon_path:
            img = load_image(icon_path, (64, 64))
            if img:
                img = img.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)
                mime_image_placeholder.set_from_pixbuf(img)
                current_mime_icon_path = icon_path
                return
    # If not found, show placeholder
    print("DEBUG: No icon found")
    mime_image_placeholder.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
    if current_mime_name:
        current_mime_icon_path = f"/fake/{current_mime_name}.png"

mime_right = Gtk.Frame()
mime_right.set_label("Extension details")
mime_frame.pack_end(mime_right, True, True, 0)
mime_right.set_margin_start(6)

mime_right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=6)
mime_right.add(mime_right_box)

mime_info_label = Gtk.Label(label="Select an extension on the left")
mime_info_label.set_alignment(0.5, 0.5)
mime_right_box.pack_start(mime_info_label, False, False, 10)

mime_image_placeholder = Gtk.Image()
mime_image_placeholder.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
mime_image_placeholder.set_pixel_size(64)
mime_right_box.pack_start(mime_image_placeholder, False, False, 10)

def on_change_mime_click():
    global current_mime_icon_path
    zenity_cmd = ['zenity', '--file-selection', '--title=Choose an icon', '--file-filter=Images | *.png *.svg *.xpm']
    result = subprocess.run(zenity_cmd, capture_output=True, text=True)
    chemin_selectionne = result.stdout.strip()

    if chemin_selectionne and current_mime_name:
        fake_original = f"/fake/{current_mime_name}.png"
        dest_path = apply_new_icon(theme_name, "mimetypes", chemin_selectionne, fake_original)
        if dest_path:
            refresh_icone_widget(mime_image_placeholder, dest_path, load_image)
            current_mime_icon_path = str(dest_path)

btn_change_mime_icon = Gtk.Button(label="Change")
btn_change_mime_icon.connect("clicked", lambda *args: on_change_mime_click())
mime_right_box.pack_start(btn_change_mime_icon, False, False, 0)

mime_selection_handler_id = mime_list.get_selection().connect("changed", on_mime_select)
mime_search_var.connect("changed", lambda *args: refresh_list(mime_list, mime_search_var, mime_list.get_selection(), mime_selection_handler_id))


# Barre du bas
bottom_bar = Gtk.ActionBar()
root_vbox.pack_end(bottom_bar, False, False, 0)

btn_import = Gtk.Button(label="Import Theme")
btn_import.connect("clicked", lambda *args: import_theme())
bottom_bar.pack_end(btn_import)

btn_export = Gtk.Button(label="Export Theme")
btn_export.connect("clicked", lambda *args: export_theme())
bottom_bar.pack_end(btn_export)

btn_help = Gtk.Button(label="Help")
btn_help.connect("clicked", lambda *args: show_help())
bottom_bar.pack_end(btn_help)

# popup de sauvegarde

def ask_unsaved_changes(root):
    dialog = Gtk.Dialog()
    dialog.set_title("Unsaved changes")
    dialog.set_default_size(300, 150)
    dialog.set_transient_for(root)
    dialog.set_modal(True)

    box = dialog.get_content_area()
    label = Gtk.Label(label="You have unsaved changes.\nWhat do you want to do ?")
    box.pack_start(label, True, True, 15)

    result = {"choice": None}

    def save():
        result["choice"] = "save"
        dialog.destroy()

    def reset():
        result["choice"] = "reset"
        changeFalse()
        dialog.destroy()

    def cancel():
        result["choice"] = "cancel"
        dialog.destroy()

    btn_box = Gtk.Box(spacing=6)
    box.pack_start(btn_box, False, False, 10)

    btn_save = Gtk.Button(label="Save")
    btn_save.connect("clicked", lambda *args: save())
    btn_box.pack_start(btn_save, False, False, 5)

    btn_reset = Gtk.Button(label="Reset changes")
    btn_reset.connect("clicked", lambda *args: reset())
    btn_box.pack_start(btn_reset, False, False, 5)

    btn_cancel = Gtk.Button(label="Cancel")
    btn_cancel.connect("clicked", lambda *args: cancel())
    btn_box.pack_start(btn_cancel, False, False, 5)

    dialog.show_all()
    dialog.run()
    return result["choice"]

# Variable globale pour stocker le thème précédent
previous_theme_name = None

def on_theme_change(event):
    global theme_name, previous_theme_name
    print(theme_name)
    
    selection = theme_listbox.get_selection()
    if not selection:
        print("no selection, skipping")
        return
    model, treeiter = selection.get_selected()
    if not treeiter:
        return
    
    # Nouvelle sélection
    new_theme_name = model.get_value(treeiter, 0)
    
    # Vérifier les changements non sauvegardés
    if has_unsaved_changes():
        choice = ask_unsaved_changes(root)

        if choice == "cancel":
            # Bloquer le signal pour éviter une boucle infinie
            selection.handler_block_by_func(on_theme_change)
            # Réélectionner le thème précédent
            if previous_theme_name:
                for i, row in enumerate(model):
                    if row[0] == previous_theme_name:
                        theme_listbox.set_cursor(i, None)
                        break
            selection.handler_unblock_by_func(on_theme_change)
            return
        elif choice == "save":
            save_theme(theme_name)
        elif choice == "reset":
            reset_theme(theme_name)
    
    # Continuer normalement
    changeFalse()
    theme_name = new_theme_name
    previous_theme_name = new_theme_name
    print(theme_name)
    on_theme_select(None, theme_listbox, tabs, entry_name)

theme_name = ""
refresh_theme_listbox(theme_listbox)
theme_listbox.get_selection().connect("changed", on_theme_change)

# Initialiser previous_theme_name avec le premier thème sélectionné
selection = theme_listbox.get_selection()
if selection:
    model, treeiter = selection.get_selected()
    if treeiter:
        previous_theme_name = model.get_value(treeiter, 0)

def on_close(*args):
    if has_unsaved_changes():
        choice = ask_unsaved_changes(root)

        if choice == "cancel":
            return True  # Bloquer la fermeture

        elif choice == "save":
            save_theme(theme_name)

        elif choice == "reset":
            reset_theme(theme_name)

    return False  # Permettre la fermeture

root.connect("delete-event", on_close)
root.show_all()
Gtk.main()
