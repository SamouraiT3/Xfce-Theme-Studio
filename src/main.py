import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib
from pathlib import Path
import cairosvg
from io import BytesIO
from PIL import Image
import subprocess
import os
import shutil
import tarfile
import webbrowser
import sys

from icon_engine import tab_click, display_icon, best_icon
from theme_manage import (
    create_theme_popup,
    delete_theme_popup,
    refresh_theme_listbox,
    on_theme_select,
    save_theme,
    reset_theme,
    USER_PATH,
    SYSTEM_PATH,
    list_themes,
    get_theme_dirs_with_inheritance,
    rename_theme,
    find_theme_path,
    create_gtk_theme_popup,
    delete_gtk_theme_popup,
    refresh_gtk_theme_listbox,
    on_gtk_theme_select,
    save_gtk_theme,
    reset_gtk_theme,
    rename_gtk_theme,
    list_gtk_themes,
)
from icon_modify import apply_new_icon, refresh_icone_widget, refresh_icon_cell, has_unsaved_changes, changeFalse, modifications_en_cours
from mimetype_tab import refresh_list, items, displayed
import update_manager

# Main window
root = Gtk.Window()
root.set_title("Xfce Theme Studio -- Create and customize theme")
root.set_icon_name("xfce-theme-studio")
root.set_default_size(975, 650)
root.set_resizable(True)

# CSS for highlighting selected icons
css_provider = Gtk.CssProvider()
css_provider.load_from_data(b"""
    .icon-cell-selected {
        border: 2px solid @theme_selected_bg_color;
        border-radius: 6px;
        background-color: alpha(@theme_selected_bg_color, 0.15);
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

current_mode = "icons"

# on defnis askstring
def askstring(title, message, default=""):
    dialog = Gtk.Dialog(title, root, 0, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
    dialog.set_default_size(300, 100)

    box = dialog.get_content_area()
    label = Gtk.Label(label=message)
    entry = Gtk.Entry()
    entry.set_text(default)

    box.pack_start(label, True, True, 5)
    box.pack_start(entry, True, True, 5)
    dialog.show_all()

    response = dialog.run()
    text = entry.get_text()
    dialog.destroy()

    if response == Gtk.ResponseType.OK:
        return text
    else:
        return None


def is_icon_mode():
    return current_mode == "icons"


def refresh_mode_theme_listbox():
    if is_icon_mode():
        refresh_theme_listbox(theme_listbox)
    else:
        refresh_gtk_theme_listbox(theme_listbox)


def update_mode_display():
    mode_button.set_label(
    "Icon themes" if is_icon_mode() else "GTK/XFWM4 themes"
    )
    entry_name.set_text("")
    left_frame.set_label("Custom themes" if is_icon_mode() else "GTK/XFWM4 themes")
    if is_icon_mode():
        help_label.set_text("Enter the icon theme name and press Enter to rename it.")
        right_content_stack.set_visible_child(icon_content_box)
    else:
        help_label.set_text("Select a GTK/XFWM4 theme and use the header actions to create or delete custom GTK themes.")
        right_content_stack.set_visible_child(gtk_details_box)

    refresh_mode_theme_listbox()


def on_new_theme():
    if is_icon_mode():
        create_theme_popup(root, theme_listbox)
    else:
        create_gtk_theme_popup(root, theme_listbox)


def on_delete_theme():
    if is_icon_mode():
        delete_theme_popup(root, theme_listbox)
    else:
        delete_gtk_theme_popup(root, theme_listbox)


def on_save_theme_action():
    global theme_name
    if is_icon_mode():
        save_theme(theme_name)
        messagebox_showinfo("Saved", f"Icon theme '{theme_name}' saved.")
    else:
        message = save_gtk_theme(theme_name)
        messagebox_showinfo("GTK/XFWM4 Save", message)


def on_reset_theme_action():
    global theme_name
    if is_icon_mode():
        reset_theme(theme_name)
        messagebox_showinfo("Reset", f"Icon theme '{theme_name}' reset.")
    else:
        message = reset_gtk_theme(theme_name)
        messagebox_showinfo("GTK/XFWM4 Reset", message)


def on_mode_switch(combo):
    global current_mode
    text = combo.get_active_text()
    current_mode = "icons" if text == "Icon themes" else "gtk"
    update_mode_display()


def get_downloads_dir():
    """Get the user's Downloads directory using XDG standards."""
    try:
        result = subprocess.run(['xdg-user-dir', 'DOWNLOAD'], capture_output=True, text=True, check=False)
        downloads_dir = result.stdout.strip()
        if downloads_dir and os.path.isdir(downloads_dir):
            return downloads_dir
    except Exception:
        pass
    
    # Fallback to common locations
    fallback_dirs = [
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Téléchargements"),
        os.path.expanduser("~/Download"),
    ]
    
    for fallback_dir in fallback_dirs:
        if os.path.isdir(fallback_dir):
            return fallback_dir
    
    # Create and return ~/Downloads if nothing else works
    downloads_dir = os.path.expanduser("~/Downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    return downloads_dir


def import_theme_from_file(file_path, silent=False):
    """Import a theme from a specific file. Returns True on success, False on failure."""
    if not os.path.isfile(file_path):
        if not silent:
            messagebox_showerror("Error", f"File not found: {file_path}")
        return False
    
    if not file_path.lower().endswith(('.tar.gz', '.tgz', '.zip', '.xts')):
        if not silent:
            messagebox_showerror("Error", "Unsupported file format. Please select a .xts, .tar.gz, .zip file.")
        return False
    
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir)
        
        try:
            if file_path.lower().endswith('.zip'):
                import zipfile
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:
                with tarfile.open(file_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)
            
            # Check for metadata file
            metadata_file = os.path.join(extract_dir, '.theme-info')
            theme_type = None  # 'icons' or 'gtk'
            theme_name = None
            
            if os.path.isfile(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = {}
                        for line in f:
                            if '=' in line:
                                key, val = line.strip().split('=', 1)
                                metadata[key] = val
                        theme_name = metadata.get('name')
                        theme_type = metadata.get('type')  # 'icons' or 'gtk'
                except Exception:
                    theme_type = None
            
            if not theme_type:
                # Try to infer from directory structure
                extracted_items = os.listdir(extract_dir)
                extracted_items = [item for item in extracted_items if item != '.theme-info']
                
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                    theme_source_dir = os.path.join(extract_dir, extracted_items[0])
                    if not theme_name:
                        theme_name = extracted_items[0]
                    # Infer type from structure
                    theme_files = os.listdir(theme_source_dir)
                    if any(f in theme_files for f in ['index.theme', 'mimetypes', 'places', 'apps', 'actions']):
                        theme_type = 'icons'
                    else:
                        theme_type = 'gtk'
                else:
                    # Multiple items or files
                    file_name = os.path.basename(file_path)
                    if file_name.lower().endswith('.tar.gz'):
                        theme_name = os.path.splitext(os.path.splitext(file_name)[0])[0]
                    else:
                        theme_name = os.path.splitext(file_name)[0]
                    theme_source_dir = extract_dir
                    theme_type = 'icons' if is_icon_mode() else 'gtk'
            else:
                # Use metadata to find theme dir
                extracted_items = os.listdir(extract_dir)
                extracted_items = [item for item in extracted_items if item != '.theme-info']
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                    theme_source_dir = os.path.join(extract_dir, extracted_items[0])
                else:
                    theme_source_dir = extract_dir
            
            # Copy to appropriate user themes location
            if theme_type == 'icons':
                system, custom = list_themes()
                dest = os.path.join(USER_PATH, theme_name)
            else:
                system, custom = list_gtk_themes()
                dest = os.path.join(os.path.expanduser("~/.themes"), theme_name)
            
            if theme_name in system or theme_name in custom:
                if not silent:
                    overwrite = messagebox_askyesno(
                        "Overwrite theme?",
                        f"The theme '{theme_name}' already exists. Overwrite?"
                    )
                    if not overwrite:
                        return False
                else:
                    # In silent mode, skip existing themes
                    return False
                shutil.rmtree(dest, ignore_errors=True)
            
            shutil.copytree(theme_source_dir, dest, dirs_exist_ok=True)
            if not silent:
                messagebox_showinfo("Success", f"Theme '{theme_name}' imported from archive")
            refresh_mode_theme_listbox()
            return True
            
        except Exception as e:
            if not silent:
                messagebox_showerror("Error", f"Failed to import theme: {e}")
            return False


def import_theme():
    downloads_dir = get_downloads_dir()
    zenity_cmd = ['zenity', '--file-selection', '--title=Import Theme', '--file-filter=Themes | *.xts *.tar.gz *.zip', '--filename=' + downloads_dir + '/']
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

    # Use the generic import function
    if os.path.isfile(selected_path):
        import_theme_from_file(selected_path, silent=False)
    elif os.path.isdir(selected_path):
        # Handle directory import
        theme_name = os.path.basename(os.path.normpath(selected_path))
        if is_icon_mode():
            system, custom = list_themes()
            dest = os.path.join(USER_PATH, theme_name)
        else:
            system, custom = list_gtk_themes()
            dest = os.path.join(os.path.expanduser("~/.themes"), theme_name)

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
            refresh_mode_theme_listbox()
        except Exception as e:
            messagebox_showerror("Error", f"Import failed: {e}")

def export_theme():
    global theme_name
    if not theme_name:
        messagebox_showerror("Error", "Select a theme first")
        return

    source_dir = find_theme_path(theme_name, mode="icons" if is_icon_mode() else "gtk")
    if not source_dir or not os.path.isdir(source_dir):
        messagebox_showerror("Error", "Theme folder not found")
        return

    downloads_dir = get_downloads_dir()
    
    zenity_cmd = ['zenity', '--file-selection', '--save', '--title=Export Theme', '--filename=' + os.path.join(downloads_dir, f"{theme_name}.xts")]
    result = subprocess.run(zenity_cmd, capture_output=True, text=True)
    target_file = result.stdout.strip()
    
    if not target_file:
        return

    # Add .xts extension if not present
    if not target_file.lower().endswith('.xts'):
        target_file += '.xts'

    try:
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_extract = os.path.join(temp_dir, "archive_content")
            os.makedirs(temp_extract)
            
            # Copy theme to temp location
            temp_theme = os.path.join(temp_extract, os.path.basename(source_dir))
            shutil.copytree(source_dir, temp_theme)
            
            # Create metadata file
            theme_type = 'icons' if is_icon_mode() else 'gtk'
            metadata_file = os.path.join(temp_extract, '.theme-info')
            with open(metadata_file, 'w') as f:
                f.write(f"name={theme_name}\n")
                f.write(f"type={theme_type}\n")
            
            # Create archive with metadata and theme
            with tarfile.open(target_file, "w:gz") as tar:
                tar.add(temp_extract, arcname='.')
        
        messagebox_showinfo("Success", f"Theme exported to {target_file}")
    except Exception as e:
        messagebox_showerror("Error", f"Export failed: {e}")

def get_theme_archive_info(file_path):
    """
    Retourne (theme_name, theme_type) ou (None, None) si impossible.
    Les types acceptés sont uniquement 'icons' et 'gtk'.
    """
    if not os.path.isfile(file_path):
        return None, None

    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        extract_dir = os.path.join(temp_dir, "extract")
        os.makedirs(extract_dir)

        try:
            if file_path.lower().endswith(".zip"):
                import zipfile
                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:
                with tarfile.open(file_path, "r:gz") as tar_ref:
                    tar_ref.extractall(extract_dir)

            metadata_file = os.path.join(extract_dir, ".theme-info")

            if os.path.isfile(metadata_file):
                metadata = {}

                with open(metadata_file, "r") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            metadata[key] = value

                theme_name = metadata.get("name")
                theme_type = metadata.get("type")

                if theme_type not in ("icons", "gtk"):
                    return None, None

                return theme_name, theme_type

            return None, None

        except Exception:
            return None, None
        
def ask_import_theme(file_path):
    theme_name, theme_type = get_theme_archive_info(file_path)

    if not theme_name or theme_type not in ("icons", "gtk"):
        messagebox_showerror(
            "Import impossible",
            "Le fichier ne contient pas de métadonnées valides.\n"
            "Type accepté : icons ou gtk."
        )
        return False

    return messagebox_askyesno(
        "Importer le thème",
        f"Nom : {theme_name}\n"
        f"Type : {theme_type}\n\n"
        f"Voulez-vous importer ce thème ?"
    )


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

    if is_icon_mode():
        success, error = rename_theme(theme_name, new_name)
    else:
        success, error = rename_gtk_theme(theme_name, new_name)

    if not success:
        messagebox_showerror("Error", error)
        entry_name.set_text(theme_name)
        return

    messagebox_showinfo("Success", f"Theme renamed to {new_name}")
    
    if is_icon_mode():
        try:
            result = subprocess.run(['xfconf-query', '-c', 'xsettings', '-p', '/Net/IconThemeName'], 
                                  capture_output=True, text=True)
            current_system_theme = result.stdout.strip() if result.returncode == 0 else None
            
            if current_system_theme == theme_name:
                subprocess.run(['xfconf-query', '-c', 'xsettings', '-p', '/Net/IconThemeName', '-s', new_name],
                             capture_output=True)
        except Exception as e:
            print(f"Could not update system theme: {e}")

    theme_name = new_name
    refresh_mode_theme_listbox()

    model = theme_listbox.get_model()
    for i, row in enumerate(model):
        if row[0] == theme_name:
            theme_listbox.set_cursor(i, None)
            if is_icon_mode():
                on_theme_select(None, theme_listbox, tabs, entry_name)
            else:
                on_gtk_theme_select(None, theme_listbox, entry_name, gtk_details_label, gtk_structure_box)
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
        
        # Convert via PNG in memory → GdkPixbuf copies the data (avoids new_from_data GC bug)
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
    items_to_load = []

    def load_icons_batch(start_idx):
        """Load icons asynchronously in batches"""
        batch_size = 6
        end_idx = min(start_idx + batch_size, len(items_to_load))
        
        for i in range(start_idx, end_idx):
            item_data = items_to_load[i]
            img_widget = item_data["img_widget"]
            vbox = item_data["vbox"]
            item = item_data["item"]
            
            icon_img = load_image(item["path"], (64, 64))
            if icon_img:
                icon_img = icon_img.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)
                GLib.idle_add(img_widget.set_from_pixbuf, icon_img)
                item_data["corrupted"] = False
            else:
                # Mark as corrupted
                def set_corrupted(vbox_ref, img_ref):
                    vbox_ref.remove(img_ref)
                    label = Gtk.Label(label="Corrupted")
                    label.set_size_request(64, 64)
                    vbox_ref.pack_start(label, False, False, 4)
                    label.show()
                    return False
                GLib.idle_add(set_corrupted, vbox, img_widget)
                item_data["corrupted"] = True
        
        # Schedule next batch
        if end_idx < len(items_to_load):
            GLib.idle_add(load_icons_batch, end_idx)
        
        return False

    def select_item(item, widget):
        is_corrupted = False
        for item_data in items_to_load:
            if item_data["item"] is item:
                is_corrupted = item_data.get("corrupted", False)
                break
        
        if selected_widget["widget"]:
            old_widget = selected_widget["widget"]
            old_widget.set_state_flags(Gtk.StateFlags.NORMAL, True)
            old_widget.get_style_context().remove_class("icon-cell-selected")
        selected_item["item"] = item
        selected_widget["widget"] = widget
        widget.set_state_flags(Gtk.StateFlags.SELECTED, True)
        widget.get_style_context().add_class("icon-cell-selected")
        
        # Disable use button if corrupted
        use_btn.set_sensitive(not is_corrupted)

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
        items_to_load.clear()
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

            # Create empty image widget for lazy loading
            img = Gtk.Image()
            img.set_size_request(64, 64)
            vbox.pack_start(img, False, False, 4)

            theme_label = Gtk.Label(label=item["theme"])
            theme_label.set_line_wrap(True)
            theme_label.set_width_chars(15)
            vbox.pack_start(theme_label, False, False, 4)

            item_data = {
                "item": item,
                "img_widget": img,
                "vbox": vbox,
                "corrupted": False
            }
            items_to_load.append(item_data)

            def make_callback(selected=item, widget=cell):
                return lambda *args: select_item(selected, widget)

            wrapper.connect("button-press-event", make_callback())

            col += 1
            if col >= columns:
                col = 0
                row += 1

        grid.show_all()
        
        # Start lazy loading
        if items_to_load:
            GLib.idle_add(load_icons_batch, 0)

    def use_selected_icon():
        if not selected_item["item"]:
            messagebox_showerror("Error", "Select an icon first")
            return
        
        # Copy the selected icon to the temp theme folder
        try:
            source_path = selected_item["item"]["path"]
            
            # Get the temporary directory for the current theme
            temp_path = Path.home() / ".xfce-theme-studio" / "theme" / f"{current_theme_name}.temp"
            dest_dir = temp_path / category.lower()  # Use the passed category
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Get the filename to replace
            dest_filename = Path(current_icon_path).name
            dest_full_path = dest_dir / dest_filename
            
            # Copy the file
            shutil.copy(source_path, dest_full_path)
            
            # Mark as modified
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

    use_btn = Gtk.Button(label="Use this icon")
    use_btn.set_sensitive(False)  # Disabled by default until an icon is selected
    use_btn.connect("clicked", lambda *args: use_selected_icon())
    btn_box.pack_start(use_btn, False, False, 0)

    btn_download = Gtk.Button(label="Download icon")
    btn_download.connect("clicked", lambda *args: download_selected_icon())
    btn_box.pack_start(btn_download, False, False, 0)

    btn_close = Gtk.Button(label="Close")
    btn_close.connect("clicked", lambda *args: popup.destroy())
    btn_box.pack_end(btn_close, False, False, 0)

    popup.show_all()

# Action bar with window buttons
toolbar = Gtk.HeaderBar()
toolbar.set_show_close_button(True)
toolbar.set_title("| Xfce Theme Studio -- Manage themes |")
root.set_titlebar(toolbar)

btn_new = Gtk.Button(label="New theme")
btn_new.connect("clicked", lambda *args: on_new_theme())
toolbar.pack_start(btn_new)

btn_delete = Gtk.Button(label="delete theme")
btn_delete.connect("clicked", lambda *args: on_delete_theme())
toolbar.pack_start(btn_delete)

btn_save = Gtk.Button(label="save")
btn_save.connect("clicked", lambda *args: on_save_theme_action())
toolbar.pack_start(btn_save)

btn_reset = Gtk.Button(label="Reset changes")
btn_reset.connect("clicked", lambda *args: on_reset_theme_action())
toolbar.pack_start(btn_reset)

# Current state
current_mode = "icons"

mode_button = Gtk.Button(label="Icon themes")
toolbar.pack_end(mode_button)

def on_mode_switch(button):
    global current_mode

    if current_mode == "icons":
        current_mode = "gtk"
        button.set_label("GTK/XFWM4 themes")

        # your code to display GTK/XFWM4
        print("Mode GTK/XFWM4")

    else:
        current_mode = "icons"
        button.set_label("Icon themes")

        # your code to display icons
        print("Mode Icon themes")
    
    update_mode_display()

mode_button.connect("clicked", on_mode_switch)

# Wrapper vertical : contient content_stack (horizontal) + bottom_bar
root_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
root.add(root_vbox)

# Cadre principal (horizontal)
main_frame = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
main_frame.set_margin_start(8)
main_frame.set_margin_end(8)
main_frame.set_margin_top(8)
main_frame.set_margin_bottom(0)
root_vbox.pack_start(main_frame, True, True, 0)

# Theme list (left)
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

# Theme details area (right)
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

help_label = Gtk.Label(label="Enter the theme name and press Enter to rename it. The changes are automatically saved to the current session.")
help_label.set_alignment(0, 0.5)
help_label.set_opacity(0.7)
right_box.pack_start(help_label, False, False, 6)

# Contenu selon le mode actif
right_content_stack = Gtk.Stack()
right_content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
right_content_stack.set_transition_duration(200)
right_box.pack_start(right_content_stack, True, True, 0)

icon_content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
right_content_stack.add_titled(icon_content_box, "icon_page", "Icon page")

gtk_details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=6)

gtk_details_label = Gtk.Label(label="Select a GTK/XFWM4 theme to see details here.")
gtk_details_label.set_alignment(0, 0)
gtk_details_label.set_line_wrap(True)
gtk_details_box.pack_start(gtk_details_label, False, False, 0)

gtk_structure_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
gtk_details_box.pack_start(gtk_structure_box, True, True, 0)

right_content_stack.add_titled(gtk_details_box, "gtk_page", "GTK page")

# Icon tabs by category

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

        # Bouton add (+) pour ajouter une icône personnalisée juste à coté de la barre de recherche
        self.btn_add_icon = Gtk.Button(label="+")
        self.btn_add_icon.set_tooltip_text("Add a custom icon for this category")
        self.btn_add_icon.connect("clicked", lambda *args: self.on_add_icon_click())
        search_holder.pack_start(self.btn_add_icon, False, False, 0)

        # Bouton remove (-) pour supprimer l'icône personnalisée sélectionnée si présent uniquement dans le dossier temporaire ou si elle est déjà présente dans le thème d'origine (permet de revenir à l'icône d'origine)
        self.btn_remove_icon = Gtk.Button(label="-")
        self.btn_remove_icon.set_tooltip_text("Remove the custom icon and revert to the original one")
        self.btn_remove_icon.connect("clicked", lambda *args: self.on_remove_icon_click())
        search_holder.pack_start(self.btn_remove_icon, False, False, 0)

        # Frame principale avec icons + preview
        self.main_frame = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.frame.pack_start(self.main_frame, True, True, 0)

        # Icons frame (scrolled window)
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

        # Embedded preview
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

        self.large_preview_images = {}  # key = icon name

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

    # Essential functions for displaying tabs

    def on_add_icon_click(self):
        if not self.current_theme_name:
            messagebox_showerror("Error", "Select a theme first")
            return

        # Ask for the new icon name
        dialog = Gtk.Dialog(title="Add custom icon", transient_for=root, modal=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Add", Gtk.ResponseType.OK)

        content_area = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_placeholder_text("Enter the new icon name (without extension)")
        content_area.pack_start(entry, True, True, 10)
        entry.show()

        response = dialog.run()
        icon_name = entry.get_text().strip()
        dialog.destroy()

        if response == Gtk.ResponseType.OK and icon_name:
            existing_paths = [item["path"] for item in self.icon_items]
            if any(Path(path).stem == icon_name for path in existing_paths):
                messagebox_showerror("Error", f"An icon named '{icon_name}' already exists in this theme.")
                return

            try:

                zenity_cmd = ['zenity', '--file-selection', '--title=Select icon for ' + icon_name, '--file-filter=Images | *.png *.svg *.xpm', '--filename=' + get_downloads_dir() + '/']
                result = subprocess.run(zenity_cmd, capture_output=True, text=True)
                selected_path = result.stdout.strip()

                if selected_path:
                    # on copie l'icone dans le dossier temporaire avec le nom choisi et l'extension d'origine
                    ext = Path(selected_path).suffix
                    dest_dir = Path.home() / ".xfce-theme-studio" / "theme" / f"{self.current_theme_name}.temp" / self.category.lower()
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_path = dest_dir / f"{icon_name}{ext}"
                    shutil.copy(selected_path, dest_path)
                    messagebox_showinfo("Success", f"Custom icon added: {dest_path.name}")

                global theme_dirs, modifications_en_cours
                theme_dirs = get_theme_dirs_with_inheritance(self.current_theme_name)
                self.icon_items, self.icon_photo_refs = self.tab_click(
                    self.category,
                    theme_dirs,
                    self.icons_container,
                    self.load_image,
                    self.on_click,
                    GRID_COLS
                )
                
                self.refresh_icons()
                modifications_en_cours = True

            except Exception as e:
                messagebox_showerror("Error", f"Failed to create custom icon: {e}")

    
    def on_remove_icon_click(self):
        if not self.current_theme_name:
            messagebox_showerror("Error", "Select a theme first")
            return

        if not self.selected_icon_cell["cell"]:
            messagebox_showerror("Error", "Select an icon first")
            return

        icon_path = self.current_icon_path
        if not icon_path:
            messagebox_showerror("Error", "No icon selected")
            return

        try:
            # on évite que le dossier commence par "/usr/share/icons"

            if icon_path.startswith("/usr/share/icons"):
                messagebox_showerror("Error", "Cannot remove system icons")
                return
            temp_icon_path = Path.home() / ".xfce-theme-studio" / "theme" / f"{self.current_theme_name}.temp" / icon_path
            if temp_icon_path.exists():
                temp_icon_path.unlink()
                messagebox_showinfo("Success", f"Custom icon removed: {icon_path}")
            else:
                messagebox_showinfo("Info", f"No custom icon to remove for: {icon_path}")

            global theme_dirs, modifications_en_cours
            theme_dirs = get_theme_dirs_with_inheritance(self.current_theme_name)
            self.icon_items, self.icon_photo_refs = self.tab_click(
                self.category,
                theme_dirs,
                self.icons_container,
                self.load_image,
                self.on_click,
                GRID_COLS
            )
            
            self.refresh_icons()
            modifications_en_cours = True

        except Exception as e:
            messagebox_showerror("Error", f"Failed to remove custom icon: {e}")

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
        
        # Check if the icon is corrupted by finding it in icon_items
        is_corrupted = False
        for item in self.icon_items:
            if item["cell"] is cell:
                is_corrupted = item.get("corrupted", False)
                break

        self.select_icon(cell, path, img, is_corrupted)

    def select_icon(self, cell, icon_id, icon_photo=None, is_corrupted=False):
        # reset previous selection
        if self.selected_icon_cell["cell"]:
            old_cell = self.selected_icon_cell["cell"]
            old_cell.set_state_flags(Gtk.StateFlags.NORMAL, True)
            old_cell.get_style_context().remove_class("icon-cell-selected")
        
        # new selection
        self.selected_icon_cell["cell"] = cell
        cell.set_state_flags(Gtk.StateFlags.SELECTED, True)
        cell.get_style_context().add_class("icon-cell-selected")

        # Disable download button if image is corrupted
        self.btn_download_icon.set_sensitive(not is_corrupted)
        
        # image preview
        img = self.load_image(icon_id, (128, 128))
        if img:
            img = img.scale_simple(128, 128, GdkPixbuf.InterpType.BILINEAR)
            self.large_preview_images[icon_id] = img
            self.large_preview.set_from_pixbuf(img)
        else:
            self.large_preview.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)

    def on_resize(self, *args):
        """Handler appelé à chaque modification de taille du canvas.
        Debounced: on ne reconstruit la grille qu'après 800 ms d'inactivité."""
        width = self.scroll_canvas.get_allocated_width()
        cell_size = 92  # largeur d'une cellule
        new_cols = max(1, width // cell_size)

        # Si un job est déjà prévu et que la nouvelle cible est identique,
        # il n'est pas nécessaire de reprogrammer la même action.
        if self.resize_job.get("id") and self.resize_job.get("cols") == new_cols:
            return

        self.resize_job["cols"] = new_cols
        try:
            job_id = self.resize_job.get("id")
            if job_id:
                GLib.source_remove(job_id)
        except Exception:
            pass

        self.resize_job["id"] = GLib.timeout_add(800, self._handle_resize)

    def _handle_resize(self):
        new_cols = self.resize_job.pop("cols", None)
        self.resize_job["id"] = None
        if new_cols is None:
            width = self.scroll_canvas.get_allocated_width()
            cell_size = 92
            new_cols = max(1, width // cell_size)

        global GRID_COLS
        if new_cols == self.current_cols["value"]:
            return False  # pas besoin de changer

        self.current_cols["value"] = new_cols
        if new_cols != 1:
            GRID_COLS = new_cols

        paths = self.search_items if self.search_items else [item["path"] for item in self.icon_items]

        new_items, _ = display_icon(
            self.icons_container,
            paths,
            self.load_image,
            self.on_click,
            GRID_COLS,
            lazy_loading=True
        )
        
        return False

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
            GRID_COLS,
            lazy_loading=True
        )

    def on_upload_click(self):
        zenity_cmd = ['zenity', '--file-selection', '--title=Choose an icon', '--file-filter=Images | *.png *.svg *.xpm']
        result = subprocess.run(zenity_cmd, capture_output=True, text=True)
        chemin_selectionne = result.stdout.strip()

        if chemin_selectionne and self.selected_icon_cell["cell"]:
            theme_name = self.current_theme_name
            # 🔹 name of the icon to replace
            icone_originale = self.current_icon_path
            
            dest_path = apply_new_icon(theme_name, self.category, chemin_selectionne, icone_originale)
            if dest_path:
                refresh_icone_widget(self.large_preview, dest_path, self.load_image)

                # update the cell in the grid
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

        # Update the grid and preview immediately
        if self.selected_icon_cell["cell"]:
            refresh_icon_cell(self.selected_icon_cell["cell"], new_path, self.load_image)
            refresh_icone_widget(self.large_preview, new_path, self.load_image)

            # Reassign click handler to point to the new path
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
        # Update icon_items
        for item in self.icon_items:
            if item["path"] == old_path:
                item["path"] = new_path
                break

        # Update search_items if search active
        for i, path in enumerate(self.search_items):
            if path == old_path:
                self.search_items[i] = new_path

        # 🔹 Update the selected cell
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

            shutil.copy(source, dest)

            messagebox_showinfo("Succès", f"Icône copiée dans :\n{dest}")

        except Exception as e:
            messagebox_showerror("Erreur", f"Impossible de copier le fichier:\n{e}")

# --- Utilisation ---
tab_parent = Gtk.Notebook()
icon_content_box.pack_start(tab_parent, True, True, 0)

categories = ["Apps", "Actions", "Places", "Status", "Devices", "Emblems"]

tabs = []
for cat in categories:
    tabs.append(IconTab(tab_parent, cat, load_image, tab_click, action_inactive))

# Specific Mimetypes tab
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
        # First search in current theme and its inheritance
        for theme_dir in theme_dirs:
            found = find_mimetype_icon(theme_dir, generic_names)
            if found:
                icon_path = found
                break

        # If not found, then search all installed themes
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

# on affiche le numéro de version dans la barre du bas à gauche
version_label = Gtk.Label(label=f"{update_manager.get_current_version() or 'unknown'}")
version_label.set_opacity(0.5)
bottom_bar.pack_start(version_label)

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

# Global variable to store the previous theme
previous_theme_name = None

def on_theme_change(event):
    global theme_name, previous_theme_name

    selection = theme_listbox.get_selection()
    if not selection:
        return
    model, treeiter = selection.get_selected()
    if not treeiter:
        return
    
    # New selection
    new_theme_name = model.get_value(treeiter, 0)
    
    # Check unsaved changes only for icon mode
    if is_icon_mode() and has_unsaved_changes():
        choice = ask_unsaved_changes(root)

        if choice == "cancel":
            selection.handler_block_by_func(on_theme_change)
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

    changeFalse()
    theme_name = new_theme_name
    previous_theme_name = new_theme_name
    if is_icon_mode():
        on_theme_select(None, theme_listbox, tabs, entry_name)
    else:
        on_gtk_theme_select(None, theme_listbox, entry_name, gtk_details_label, gtk_structure_box)

theme_name = ""
refresh_mode_theme_listbox()
theme_listbox.get_selection().connect("changed", on_theme_change)
update_mode_display()

# Initialize previous_theme_name with the first selected theme
selection = theme_listbox.get_selection()
if selection:
    model, treeiter = selection.get_selected()
    if treeiter:
        previous_theme_name = model.get_value(treeiter, 0)

def on_close(*args):
    if is_icon_mode() and has_unsaved_changes():
        choice = ask_unsaved_changes(root)

        if choice == "cancel":
            return True  # Bloquer la fermeture

        elif choice == "save":
            save_theme(theme_name)

        elif choice == "reset":
            reset_theme(theme_name)

    return False  # Permettre la fermeture


def restart_application():
    launcher = update_manager.DEFAULT_INSTALL / "xfce-theme-studio"
    if launcher.exists():
        os.execv(str(launcher), [str(launcher)])

    python = sys.executable
    os.execv(python, [python] + sys.argv)


def check_for_update():
    try:
        latest = update_manager.fetch_latest_release(update_manager.DEFAULT_REPO)
    except Exception:
        return

    current_version = update_manager.get_current_version()
    if not update_manager.is_update_available(current_version, latest["tag"]):
        return

    local_label = current_version or "aucune version installée"
    message = (
        f"Version locale : {local_label}\n"
        f"Version distante : {latest['tag']}\n"
        "Voulez-vous mettre à jour l'application ?"
    )

    if messagebox_askyesno("Mise à jour disponible", message):
        try:
            install_dir = update_manager.get_update_target()
            update_manager.perform_update(latest, install_dir=install_dir)
            messagebox_showinfo(
                "Mise à jour terminée",
                f"L'application a été mise à jour vers {latest['tag']}\n" \
                f"Emplacement : {install_dir}"
            )
            restart_application()
        except Exception as exc:
            messagebox_showerror("Erreur de mise à jour", str(exc))


root.connect("delete-event", on_close)
root.connect("destroy", Gtk.main_quit)


def verify_startup_installation():
    install_dir = update_manager.get_update_target()
    if update_manager.is_installation_complete(install_dir):
        return

    messagebox_showinfo(
        "Mise à jour nécessaire",
        "Certaines parties de l'installation sont manquantes.\n" \
        "Une mise à jour complète va être effectuée pour rétablir les éléments manquants."
    )

    try:
        latest = update_manager.fetch_latest_release(update_manager.DEFAULT_REPO)
        update_manager.perform_update(latest, install_dir=install_dir)
        messagebox_showinfo(
            "Réinstallation terminée",
            "L'installation a été rétablie avec les éléments manquants."
        )
        restart_application()
    except Exception as exc:
        messagebox_showerror("Erreur de réinstallation", str(exc))


verify_startup_installation()


if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
    file_path = sys.argv[1]

    if file_path.lower().endswith('.xts'):

        def ask_import_on_startup():
            if ask_import_theme(file_path):
                import_theme_from_file(file_path)

            return False

        GLib.idle_add(ask_import_on_startup)

check_for_update()
root.show_all()
Gtk.main()
