import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
import os
import subprocess
import re
import random
import shutil
import configparser
from pathlib import Path
from theme_structure import THEME_STRUCTURE
from PIL import Image
from gtk_manage import (
    load_and_normalize_gtk_css,
    save_gtk_css,
    get_css_value,
    read_gtk_css_blocks,
    set_property_in_theme,
    get_gtk_css_paths,
    _apply_units_on_save,
)

SYSTEM_PATH = "/usr/share/icons"
USER_PATH = os.path.expanduser("~/.local/share/icons")
FLATPAK_PATH = os.path.expanduser("/var/lib/flatpak/exports/share/icons/")
GTK_SYSTEM_PATH = "/usr/share/themes"
GTK_USER_PATH = os.path.expanduser("~/.themes")
CATEGORIES = ["apps", "places", "devices", "actions", "status", "mimetypes"]
CONTEXTS = {
    "apps": "Applications",
    "places": "Places",
    "devices": "Devices",
    "actions": "Actions",
    "status": "Status",
    "mimetypes": "Mimetypes"
}


def list_themes():
    def is_valid(path):
        return os.path.isfile(os.path.join(path, "index.theme"))

    system, custom = [], []
    for base, target in [(SYSTEM_PATH, system), (USER_PATH, custom)]:
        if os.path.exists(base):
            for name in os.listdir(base):
                full = os.path.join(base, name)
                if os.path.isdir(full) and is_valid(full):
                    target.append(name)
    return sorted(system), sorted(custom)


def get_theme_dirs_with_inheritance(theme_name):
    dirs = []
    visited = set()
    to_process = [theme_name]
    
    # Include temp directory if it exists
    temp_path = Path.home() / ".xfce-theme-studio" / "theme" / f"{theme_name}.temp"
    if temp_path.exists():
        dirs.append(str(temp_path))
    
    while to_process:
        current = to_process.pop(0)
        if current in visited:
            continue
        visited.add(current)
        dirs.append(os.path.join(USER_PATH, current))
        dirs.append(os.path.join(SYSTEM_PATH, current))
        dirs.append(os.path.join(FLATPAK_PATH, current))
        
        # Read index.theme for Inherits
        index_path = os.path.join(USER_PATH, current, "index.theme")
        if not os.path.exists(index_path):
            index_path = os.path.join(SYSTEM_PATH, current, "index.theme")
            if not os.path.exists(index_path):
                index_path = os.path.join(FLATPAK_PATH, current, "index.theme")
        
        if os.path.exists(index_path):
            config = configparser.ConfigParser()
            config.read(index_path)
            if 'Icon Theme' in config and 'Inherits' in config['Icon Theme']:
                inherits = [i.strip() for i in config['Icon Theme']['Inherits'].split(',')]
                to_process.extend(inherits)
    return dirs

############################################ create theme ###############################################

def create_theme_popup(parent, theme_listbox):
    system, custom = list_themes()

    popup = Gtk.Window()
    popup.set_title("Create Theme")
    popup.set_default_size(375, 250)
    popup.set_resizable(False)
    popup.set_transient_for(parent)
    popup.set_modal(True)

    selected_theme = {"value": ""}
    name_var = {"value": ""}
    search_var = {"value": ""}

    # -------- LOGIC --------

    def generate_name(base):
        existing = os.listdir(USER_PATH) if os.path.exists(USER_PATH) else []
        i = 1
        while True:
            name = f"{base} (custom{i})"
            if name not in existing:
                return name
            i += 1

    def read_inherits(theme):
        for base in [USER_PATH, SYSTEM_PATH]:
            path = os.path.join(base, theme, "index.theme")
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("Inherits="):
                            return [i.strip() for i in line.split("=")[1].split(",")]
        return []

    # -------- UI --------

    main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    main_box.set_margin_start(10)
    main_box.set_margin_end(10)
    main_box.set_margin_top(10)
    main_box.set_margin_bottom(10)
    popup.add(main_box)

    # Left side
    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    main_box.pack_start(left, True, True, 0)

    search_entry = Gtk.Entry()
    search_entry.set_placeholder_text("Search...")
    left.pack_start(search_entry, False, False, 0)

    listbox_frame = Gtk.Frame()
    left.pack_start(listbox_frame, True, True, 0)

    # Create TreeView for themes
    theme_store = Gtk.ListStore(str)
    listbox = Gtk.TreeView(model=theme_store)
    listbox.set_headers_visible(False)

    renderer = Gtk.CellRendererText()
    column = Gtk.TreeViewColumn("Theme", renderer, text=0)
    listbox.append_column(column)

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.add(listbox)
    listbox_frame.add(scrolled)

    # Right side
    right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    main_box.pack_start(right, True, True, 0)

    lbl_base = Gtk.Label(label="Base Theme:")
    lbl_base.set_alignment(0, 0.5)
    right.pack_start(lbl_base, False, False, 0)

    base_label = Gtk.Label(label="None")
    base_label.set_alignment(0, 0.5)
    right.pack_start(base_label, False, False, 0)

    lbl_name = Gtk.Label(label="Theme Name:")
    lbl_name.set_alignment(0, 0.5)
    right.pack_start(lbl_name, False, False, 0)

    name_entry = Gtk.Entry()
    right.pack_start(name_entry, False, False, 0)

    btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    right.pack_end(btn_box, False, False, 0)

    def refresh():
        q = search_entry.get_text().lower()
        theme_store.clear()

        # System themes section
        theme_store.append(["—— System Themes ——"])
        for t in system:
            if q in t.lower():
                theme_store.append([t])

        theme_store.append([""])
        theme_store.append(["—— Custom Themes ——"])
        for t in custom:
            if q in t.lower():
                theme_store.append([t])

    def on_select(selection):
        model, treeiter = selection.get_selected()
        if not treeiter:
            return
        val = model.get_value(treeiter, 0)
        if val.startswith("——") or val == "":
            return
        selected_theme["value"] = val
        base_label.set_text(val)
        name_entry.set_text(generate_name(val))

    selection = listbox.get_selection()
    selection.connect("changed", on_select)

    search_entry.connect("changed", lambda *args: refresh())
    refresh()

    def create_theme():
        base = selected_theme["value"]
        name = name_entry.get_text().strip()

        if not base:
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Select a base theme")
            dialog.run()
            dialog.destroy()
            return
        if not name:
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Invalid name")
            dialog.run()
            dialog.destroy()
            return
        if name in system or name in custom:
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Theme already exists")
            dialog.run()
            dialog.destroy()
            return
        if not re.match(r"^[^/\\]+$", name):
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Invalid characters")
            dialog.run()
            dialog.destroy()
            return

        path = os.path.join(USER_PATH, name)
        os.makedirs(path, exist_ok=True)

        if base in custom:
            # Duplicate the custom base theme so the new theme remains independent
            base_path = os.path.join(USER_PATH, base)
            shutil.copytree(base_path, path, dirs_exist_ok=True)

            index_path = os.path.join(path, "index.theme")
            if os.path.isfile(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                with open(index_path, "w", encoding="utf-8") as f:
                    for line in lines:
                        if line.startswith("Name="):
                            f.write(f"Name={name}\n")
                        elif line.startswith("Comment="):
                            f.write(f"Comment=Theme based on {base}\n")
                        elif line.startswith("Inherits="):
                            inherits = [i.strip() for i in line.split("=", 1)[1].split(",") if i.strip() and i.strip() != base]
                            if inherits:
                                f.write(f"Inherits={','.join(inherits)}\n")
                            else:
                                f.write("Inherits=\n")
                        else:
                            f.write(line)
        else:
            inherits = read_inherits(base)
            final_inherits = [base] + [i for i in inherits if i != base]

            for cat in CATEGORIES:
                os.makedirs(os.path.join(path, cat), exist_ok=True)

            with open(os.path.join(path, "index.theme"), "w", encoding="utf-8") as f:
                # header
                f.write("[Icon Theme]\n")
                f.write(f"Name={name}\n")
                f.write(f"Comment=Theme based on {base}\n")
                f.write(f"Inherits={','.join(final_inherits)}\n")
                f.write(f"Directories={','.join(CATEGORIES)}\n\n")
    
                # sections automatiques
                for cat in CATEGORIES:
                    f.write(f"[{cat}]\n")
                    f.write(f"Size=64\n")
                    f.write(f"Context={CONTEXTS[cat]}\n")
                    f.write("Type=Fixed\n\n")

        dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, "Theme created")
        dialog.run()
        dialog.destroy()
        popup.destroy()
        refresh_theme_listbox(theme_listbox)

    btn_create = Gtk.Button(label="Create")
    btn_create.connect("clicked", lambda *args: create_theme())
    btn_box.pack_start(btn_create, True, True, 0)

    btn_cancel = Gtk.Button(label="Cancel")
    btn_cancel.connect("clicked", lambda *args: popup.destroy())
    btn_box.pack_start(btn_cancel, True, True, 0)

    popup.show_all()


################################ delete theme ####################################
    
def delete_theme_popup(parent, theme_listbox):
    _, custom = list_themes()  # only take custom themes

    if not custom:
        dialog = Gtk.MessageDialog(parent, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, "No custom themes to delete.")
        dialog.run()
        dialog.destroy()
        return

    popup = Gtk.Window()
    popup.set_title("Delete Theme")
    popup.set_default_size(375, 250)
    popup.set_resizable(False)
    popup.set_transient_for(parent)
    popup.set_modal(True)

    selected_theme = {"value": ""}

    # -------- UI --------

    main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    main_box.set_margin_start(10)
    main_box.set_margin_end(10)
    main_box.set_margin_top(10)
    main_box.set_margin_bottom(10)
    popup.add(main_box)

    # Left side
    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    main_box.pack_start(left, True, True, 0)

    search_entry = Gtk.Entry()
    search_entry.set_placeholder_text("Search...")
    left.pack_start(search_entry, False, False, 0)

    listbox_frame = Gtk.Frame()
    left.pack_start(listbox_frame, True, True, 0)

    # Create TreeView for themes
    theme_store = Gtk.ListStore(str)
    listbox = Gtk.TreeView(model=theme_store)
    listbox.set_headers_visible(False)

    renderer = Gtk.CellRendererText()
    column = Gtk.TreeViewColumn("Theme", renderer, text=0)
    listbox.append_column(column)

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.add(listbox)
    listbox_frame.add(scrolled)

    # Right side
    right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    main_box.pack_start(right, True, True, 0)

    lbl_selected = Gtk.Label(label="Selected Theme:")
    lbl_selected.set_alignment(0, 0.5)
    right.pack_start(lbl_selected, False, False, 0)

    theme_label = Gtk.Label(label="None")
    theme_label.set_alignment(0, 0.5)
    right.pack_start(theme_label, False, False, 0)

    lbl_confirm = Gtk.Label(label="Theme name to confirm:")
    lbl_confirm.set_alignment(0, 0.5)
    right.pack_start(lbl_confirm, False, False, 0)

    name_entry = Gtk.Entry()
    right.pack_start(name_entry, False, False, 0)

    btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    right.pack_end(btn_box, False, False, 0)

    def refresh():
        q = search_entry.get_text().lower()
        theme_store.clear()

        theme_store.append(["—— Custom Themes ——"])
        for t in custom:
            if q in t.lower():
                theme_store.append([t])

    def on_select(selection):
        model, treeiter = selection.get_selected()
        if not treeiter:
            return
        val = model.get_value(treeiter, 0)
        if val.startswith("——") or val == "":
            return
        selected_theme["value"] = val
        theme_label.set_text(val)

    selection = listbox.get_selection()
    selection.connect("changed", on_select)

    search_entry.connect("changed", lambda *args: refresh())
    refresh()

    def delete_theme():
        theme = selected_theme["value"]
        if not theme:
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Select a theme")
            dialog.run()
            dialog.destroy()
            return

        name_confirm = name_entry.get_text().strip()
        if name_confirm != theme:
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Name does not match")
            dialog.run()
            dialog.destroy()
            name_entry.set_text("")
            return

        path = os.path.join(USER_PATH, theme)
        try:
            shutil.rmtree(path)
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, f"Theme '{theme}' deleted")
            dialog.run()
            dialog.destroy()
            popup.destroy()
            refresh_theme_listbox(theme_listbox)
        except Exception as e:
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, f"Failed to delete: {e}")
            dialog.run()
            dialog.destroy()

    btn_delete = Gtk.Button(label="Delete")
    btn_delete.connect("clicked", lambda *args: delete_theme())
    btn_box.pack_start(btn_delete, True, True, 0)

    btn_cancel = Gtk.Button(label="Cancel")
    btn_cancel.connect("clicked", lambda *args: popup.destroy())
    btn_box.pack_start(btn_cancel, True, True, 0)

    popup.show_all()

########################## refresh listbox #############################

def refresh_theme_listbox(theme_listbox):
    _, theme_list = list_themes()
    # Clear the model
    model = theme_listbox.get_model()
    if model:
        model.clear()
    else:
        # Create new model if none exists
        model = Gtk.ListStore(str)
        theme_listbox.set_model(model)
    
    for theme in theme_list:
        model.append([theme])

################## update selected theme ####################


def find_theme_path(name, mode="icons"):
    if mode == "gtk":
        local = os.path.join(GTK_USER_PATH, name)
        if os.path.isdir(local):
            return local

        system = os.path.join(GTK_SYSTEM_PATH, name)
        if os.path.isdir(system):
            return system

        return None

    # prefer custom over system
    local = os.path.join(USER_PATH, name)
    if os.path.isdir(local):
        return local

    system = os.path.join(SYSTEM_PATH, name)
    if os.path.isdir(system):
        return system

    return None

###################################### GTK THEME EDITOR UI ######################################


def list_gtk_themes():
    def is_valid(path):
        return os.path.isfile(os.path.join(path, "index.theme"))

    system, custom = [], []
    for base, target in [(GTK_SYSTEM_PATH, system), (GTK_USER_PATH, custom)]:
        if os.path.exists(base):
            for name in os.listdir(base):
                full = os.path.join(base, name)
                if os.path.isdir(full) and is_valid(full):
                    target.append(name)
    return sorted(system), sorted(custom)


def refresh_gtk_theme_listbox(theme_listbox):
    _, theme_list = list_gtk_themes()
    model = theme_listbox.get_model()
    if model:
        model.clear()
    else:
        model = Gtk.ListStore(str)
        theme_listbox.set_model(model)

    for theme in theme_list:
        model.append([theme])


def rename_gtk_theme(old_name, new_name):
    if old_name == new_name:
        return True, ""

    if not re.match(r"^[^/\\\\]+$", new_name):
        return False, "Invalid theme name"

    system, custom = list_gtk_themes()
    if new_name in system or new_name in custom:
        return False, "A theme with that name already exists"

    old_path = os.path.join(GTK_USER_PATH, old_name)
    new_path = os.path.join(GTK_USER_PATH, new_name)
    if not os.path.isdir(old_path):
        return False, "Original theme not found"

    try:
        os.rename(old_path, new_path)

        old_temp = Path.home() / ".xfce-theme-studio" / "gtk-theme" / f"{old_name}.temp"
        new_temp = Path.home() / ".xfce-theme-studio" / "gtk-theme" / f"{new_name}.temp"
        if old_temp.exists():
            old_temp.rename(new_temp)

        index_file = os.path.join(new_path, "index.theme")
        if os.path.isfile(index_file):
            with open(index_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            with open(index_file, "w", encoding="utf-8") as f:
                for line in lines:
                    if line.startswith("Name="):
                        f.write(f"Name={new_name}\n")
                    else:
                        f.write(line)

        return True, ""
    except Exception as e:
        return False, f"Failed to rename theme: {e}"


def find_gtk_theme_path(name):
    return find_theme_path(name, mode="gtk")


def create_gtk_theme_popup(parent, theme_listbox):
    system, custom = list_gtk_themes()

    popup = Gtk.Window()
    popup.set_title("Create GTK/XFWM4 Theme")
    popup.set_default_size(400, 300)
    popup.set_resizable(False)
    popup.set_transient_for(parent)
    popup.set_modal(True)

    selected_theme = {"value": ""}

    main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    main_box.set_margin_start(10)
    main_box.set_margin_end(10)
    main_box.set_margin_top(10)
    main_box.set_margin_bottom(10)
    popup.add(main_box)

    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    main_box.pack_start(left, True, True, 0)

    search_entry = Gtk.Entry()
    search_entry.set_placeholder_text("Search base theme...")
    left.pack_start(search_entry, False, False, 0)

    listbox_frame = Gtk.Frame()
    left.pack_start(listbox_frame, True, True, 0)

    theme_store = Gtk.ListStore(str)
    listbox = Gtk.TreeView(model=theme_store)
    listbox.set_headers_visible(False)
    renderer = Gtk.CellRendererText()
    column = Gtk.TreeViewColumn("Base theme", renderer, text=0)
    listbox.append_column(column)

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.add(listbox)
    listbox_frame.add(scrolled)

    right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    main_box.pack_start(right, True, True, 0)

    lbl_base = Gtk.Label(label="Base Theme:")
    lbl_base.set_alignment(0, 0.5)
    right.pack_start(lbl_base, False, False, 0)

    base_label = Gtk.Label(label="None")
    base_label.set_alignment(0, 0.5)
    right.pack_start(base_label, False, False, 0)

    lbl_name = Gtk.Label(label="New Theme Name:")
    lbl_name.set_alignment(0, 0.5)
    right.pack_start(lbl_name, False, False, 0)

    name_entry = Gtk.Entry()
    right.pack_start(name_entry, False, False, 0)

    btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    right.pack_end(btn_box, False, False, 0)

    def refresh():
        query = search_entry.get_text().lower()
        theme_store.clear()
        theme_store.append(["—— System Themes ——"])
        for t in system:
            if query in t.lower():
                theme_store.append([t])
        theme_store.append([""])
        theme_store.append(["—— Custom Themes ——"])
        for t in custom:
            if query in t.lower():
                theme_store.append([t])

    def on_select(selection):
        model, treeiter = selection.get_selected()
        if not treeiter:
            return
        val = model.get_value(treeiter, 0)
        if val.startswith("——") or val == "":
            return
        selected_theme["value"] = val
        base_label.set_text(val)
        if val in custom:
            name_entry.set_text(f"{val}-copy")
        else:
            name_entry.set_text(f"{val}-custom")

    selection = listbox.get_selection()
    selection.connect("changed", on_select)
    search_entry.connect("changed", lambda *args: refresh())
    refresh()

    def create_theme():
        base = selected_theme["value"]
        name = name_entry.get_text().strip()
        if not base:
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Select a base theme")
            dialog.run()
            dialog.destroy()
            return
        if not name:
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Invalid theme name")
            dialog.run()
            dialog.destroy()
            return
        if name in system or name in custom:
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Theme already exists")
            dialog.run()
            dialog.destroy()
            return
        if not re.match(r"^[^/\\\\]+$", name):
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Invalid characters")
            dialog.run()
            dialog.destroy()
            return

        src_path = os.path.join(GTK_USER_PATH if base in custom else GTK_SYSTEM_PATH, base)
        dest_path = os.path.join(GTK_USER_PATH, name)
        os.makedirs(dest_path, exist_ok=True)
        
        ALLOWED_FOLDERS = [
            "gtk-3.0",
            "xfwm4",
            "assets"
        ]

        ALLOWED_FILES = [
            "index.theme"
        ]

        for item in os.listdir(src_path):
            src_item = os.path.join(src_path, item)
            dest_item = os.path.join(dest_path, item)

            # Copy allowed folders
            if item in ALLOWED_FOLDERS and os.path.isdir(src_item):
                shutil.copytree(src_item, dest_item, dirs_exist_ok=True)

            # Copy allowed files
            elif item in ALLOWED_FILES and os.path.isfile(src_item):
                shutil.copy2(src_item, dest_item)

        index_path = os.path.join(dest_path, "index.theme")
        if os.path.isfile(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open(index_path, "w", encoding="utf-8") as f:
                for line in lines:
                    if line.startswith("Name="):
                        f.write(f"Name={name}\n")
                    elif line.startswith("Comment="):
                        f.write(f"Comment=Theme based on {base}\n")
                    else:
                        f.write(line)

        # Normalize GTK CSS in gtk-3.0
        try:
            normalized = load_and_normalize_gtk_css(dest_path)
            save_gtk_css(
                normalized)
        except Exception:
            pass  # Silently ignore if normalization fails

        dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, "GTK/XFWM4 theme created")
        dialog.run()
        dialog.destroy()
        popup.destroy()
        refresh_gtk_theme_listbox(theme_listbox)

    btn_create = Gtk.Button(label="Create")
    btn_create.connect("clicked", lambda *args: create_theme())
    btn_box.pack_start(btn_create, True, True, 0)

    btn_cancel = Gtk.Button(label="Cancel")
    btn_cancel.connect("clicked", lambda *args: popup.destroy())
    btn_box.pack_start(btn_cancel, True, True, 0)

    popup.show_all()


def clear_container(container):
    children = []
    container.foreach(children.append)
    for child in children:
        container.remove(child)


def parse_css_value(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [parse_css_value(v) for v in value]
    if not isinstance(value, str):
        return value

    value = value.strip()
    if not value:
        return value

    def clean_part(part):
        match = re.match(r'^([-0-9.]+)(px|pt|em|rem|%)?$', part)
        if match:
            num = match.group(1)
            return int(num) if re.match(r'^-?\d+$', num) else float(num)
        return part

    if '(' in value and value.endswith(')'):
        return value

    parts = re.split(r'\s+', value)
    if len(parts) > 1:
        return [clean_part(part) for part in parts]
    return clean_part(parts[0])


def create_property_widget(prop, prop_name, theme_path, inherited_value=None, double_parent=False, css_filename="gtk.css"):

    css_blocks = read_gtk_css_blocks(theme_path)

    selector = prop.get("selector")
    css_property = prop_name.replace("_", "-")

    if inherited_value is not None:
        value = inherited_value
    else:
        css_key = f"{theme_path}/gtk-3.0/{css_filename}"
        if css_key in css_blocks:
            value = get_css_value(
                css_blocks[css_key],
                selector,
                css_property
            )
        else:
            value = None
        value = parse_css_value(value)

    prop_type = prop.get("type", "text")

    if isinstance(prop_type, list) and len(prop_type) >= 2:
        defaults = prop.get("default")
        values = value if isinstance(value, list) and len(value) >= len(prop_type) else None

        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for idx, child_type in enumerate(prop_type):
            child_default = None
            if values is not None:
                child_default = values[idx]
            elif isinstance(defaults, (list, tuple)) and len(defaults) > idx:
                child_default = defaults[idx]
            else:
                child_default = defaults

            child_prop = dict(prop, type=child_type, default=child_default)
            container.pack_start(
                create_property_widget(
                    child_prop,
                    prop_name,
                    theme_path,
                    inherited_value=child_default,
                    double_parent=True,
                    css_filename=css_filename,
                ),
                False,
                False,
                0,
            )

        return container

    if prop_type.startswith("double-"):
        base_type = prop_type[len("double-"):]
        defaults = prop.get("default")

        if isinstance(value, list) and len(value) >= 2:
            defaults = [value[0], value[1]]

        first_default = None
        second_default = None
        if isinstance(defaults, (list, tuple)) and len(defaults) >= 2:
            first_default, second_default = defaults[0], defaults[1]
        else:
            first_default = defaults
            second_default = defaults

        first_prop = dict(prop, type=base_type, default=first_default)
        second_prop = dict(prop, type=base_type, default=second_default)

        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        container.pack_start(create_property_widget(first_prop, prop_name, theme_path, inherited_value=first_default, double_parent=True, css_filename=css_filename), False, False, 0)
        container.pack_start(create_property_widget(second_prop, prop_name, theme_path, inherited_value=second_default, double_parent=True, css_filename=css_filename), False, False, 0)
        return container

    widget = None

    if prop_type == "color":
        button = Gtk.ColorButton()
        default = value if value is not None else prop.get("default")
        if default:
            rgba = Gdk.RGBA()
            rgba.parse(default)
            button.set_rgba(rgba)
        widget = button

    if prop_type == "int":
        minimum = prop.get("min", 0)
        maximum = prop.get("max", 100)
        step = prop.get("step", 1)
        default = value if value is not None else prop.get("default", 0)
        adjustment = Gtk.Adjustment(default, minimum, maximum, step, step * 10, 0)
        spin = Gtk.SpinButton(adjustment=adjustment, climb_rate=1, digits=0)
        unit = prop.get("unit")
        if unit and hasattr(spin, "set_suffix"):
            spin.set_suffix(unit)
        widget = spin

    if prop_type == "slider" or prop_type == "range":
        minimum = prop.get("min", 0)
        maximum = prop.get("max", 100)
        step = prop.get("step", 1)
        default = value if value is not None else prop.get("default", minimum)
        adjustment = Gtk.Adjustment(default, minimum, maximum, step, step * 10, 0)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
        digits = 0
        if isinstance(step, (float, int)):
            if isinstance(step, float) and not step.is_integer():
                digits = len(str(step).split(".")[1].rstrip("0"))
        elif isinstance(step, str) and "." in step:
            digits = len(step.split(".")[1].rstrip("0"))
        scale.set_digits(digits)
        scale.set_value(default)
        scale.set_hexpand(False)
        if double_parent:
            scale.set_size_request(110, -1)
        else:
            scale.set_size_request(240, -1)
        widget = scale

    if prop_type == "float":
        minimum = prop.get("min", 0.0)
        maximum = prop.get("max", 100.0)
        default = value if value is not None else prop.get("default", 0.0)
        adjustment = Gtk.Adjustment(default, minimum, maximum, 0.1, 1.0, 0)
        spin = Gtk.SpinButton(adjustment=adjustment, climb_rate=0.1, digits=2)
        unit = prop.get("unit")
        if unit and hasattr(spin, "set_suffix"):
            spin.set_suffix(unit)
        widget = spin

    if prop_type == "bool":
        switch = Gtk.Switch()
        switch.set_active(bool(value) if value is not None else bool(prop.get("default", False)))
        widget = switch

    if prop_type == "enum":
        combo = Gtk.ComboBoxText()
        options = prop.get("options", [])
        for option in options:
            combo.append_text(str(option))
        default = value if value is not None else prop.get("default")
        if default in options:
            combo.set_active(options.index(default))
        widget = combo

    if prop_type == "shadow" or prop_type == "gradient":
        label = Gtk.Label(label=f"{prop_type.capitalize()} editor")
        label.set_xalign(0)
        widget = label

    if widget is None:
        entry = Gtk.Entry()
        if isinstance(value, (list, tuple)):
            entry.set_text(" ".join(str(v) for v in value))
        else:
            entry.set_text(str(value if value is not None else prop.get("default", "")))
        widget = entry

    # Attach change handlers to commit changes to temporary theme CSS
    try:
        css_property = prop_name.replace("_", "-")
        selector = prop.get("selector")

        def _get_widget_value(w):
            t = prop.get("type", "text")
            if isinstance(w, Gtk.Entry):
                return w.get_text().strip()
            if isinstance(w, Gtk.ColorButton):
                rgba = w.get_rgba()
                try:
                    return rgba.to_string()
                except Exception:
                    return f"rgba({rgba.red}, {rgba.green}, {rgba.blue}, {rgba.alpha})"
            if isinstance(w, Gtk.SpinButton):
                val = w.get_value()
                unit = prop.get("unit")
                if unit:
                    if float(val).is_integer():
                        return f"{int(val)}{unit}"
                    return f"{val}{unit}"
                if float(val).is_integer():
                    return str(int(val))
                return str(val)
            if isinstance(w, Gtk.Scale):
                val = w.get_value()
                unit = prop.get("unit")
                if unit:
                    if float(val).is_integer():
                        return f"{int(val)}{unit}"
                    return f"{val}{unit}"
                if float(val).is_integer():
                    return str(int(val))
                return str(val)
            if isinstance(w, Gtk.Switch):
                return "true" if w.get_active() else "false"
            if isinstance(w, Gtk.ComboBoxText):
                return w.get_active_text() or ""
            return ""

        def commit(_widget=None, *_args):
            # For double-parent widgets, combine both children values
            if double_parent:
                parent = widget.get_parent()
                parts = []
                for child in parent.get_children():
                    parts.append(_get_widget_value(child))
                value_str = " ".join(p for p in parts if p is not None)
            else:
                value_str = _get_widget_value(widget)

            # derive theme name and original css path
            theme_name = Path(theme_path).name
            if theme_name.endswith('.temp'):
                theme_name = theme_name[:-5]

            original_theme_dir = theme_path
            css_paths = get_gtk_css_paths(original_theme_dir)
            
            # Find the CSS file matching css_filename
            original_css = None
            for css_path in css_paths:
                if css_path.endswith(css_filename):
                    original_css = css_path
                    break
            
            # If not found, construct the path
            if original_css is None:
                original_css = os.path.join(original_theme_dir, 'gtk-3.0', css_filename)

            try:
                set_property_in_theme(theme_name, original_css, selector, css_property, value_str)
                import icon_modify
                icon_modify.modifications_en_cours = True
            except Exception as e:
                print(f"Failed to set property {css_property} for {selector}: {e}")

        # Connect appropriate signals
        if isinstance(widget, Gtk.Entry):
            widget.connect("changed", commit)
        elif isinstance(widget, Gtk.ColorButton):
            widget.connect("color-set", commit)
        elif isinstance(widget, Gtk.SpinButton):
            widget.connect("value-changed", commit)
        elif isinstance(widget, Gtk.Scale):
            widget.connect("value-changed", commit)
        elif isinstance(widget, Gtk.Switch):
            widget.connect("notify::active", commit)
        elif isinstance(widget, Gtk.ComboBoxText):
            widget.connect("changed", commit)
    except Exception as e:
        print(f"Failed to attach handler for {prop_name}: {e}")

    return widget


def _build_css_tab_content(theme_path, css_filename, theme_structure=THEME_STRUCTURE):
    """Build the content for a CSS tab (gtk.css or gtk-dark.css)."""
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scrolled.set_hexpand(True)
    scrolled.set_vexpand(True)

    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    main_box.set_margin_start(8)
    main_box.set_margin_end(8)
    main_box.set_margin_top(8)
    main_box.set_margin_bottom(8)
    scrolled.add(main_box)

    for category_name, widgets in theme_structure.items():
        category_expander = Gtk.Expander(label=category_name)
        category_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        category_box.set_margin_start(6)
        category_box.set_margin_end(6)
        category_box.set_margin_top(6)
        category_box.set_margin_bottom(6)
        category_expander.add(category_box)
        main_box.pack_start(category_expander, False, False, 0)

        for widget_name, widget_data in widgets.items():
            widget_frame = Gtk.Frame(label=widget_name)
            widget_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            widget_box.set_margin_start(6)
            widget_box.set_margin_end(6)
            widget_box.set_margin_top(6)
            widget_box.set_margin_bottom(6)
            widget_frame.add(widget_box)
            category_box.pack_start(widget_frame, False, False, 0)

            sections = widget_data.get("sections", {})
            if len(sections) == 1:
                _, properties = next(iter(sections.items()))
                for prop_name, prop_def in properties.items():
                    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                    row.set_hexpand(True)

                    label = Gtk.Label(label=prop_def.get("label", prop_name))
                    label.set_xalign(0)
                    label.set_halign(Gtk.Align.START)
                    row.pack_start(label, True, True, 0)

                    controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                    controls.set_halign(Gtk.Align.END)
                    try :
                        widget = create_property_widget(prop_def, prop_name, theme_path, css_filename=css_filename)
                    except Exception as e:
                        print(f"Error creating widget for {prop_name}: {e}")
                        widget = Gtk.Label(label="Error")

                    controls.pack_start(widget, False, False, 0)

                    row.pack_start(controls, False, False, 0)
                    widget_box.pack_start(row, False, False, 0)
            else:
                for section_name, properties in sections.items():
                    section_expander = Gtk.Expander(label=section_name)
                    section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
                    section_box.set_margin_start(4)
                    section_box.set_margin_end(4)
                    section_box.set_margin_top(4)
                    section_box.set_margin_bottom(4)
                    section_expander.add(section_box)

                    for prop_name, prop_def in properties.items():
                        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                        row.set_hexpand(True)

                        label = Gtk.Label(label=prop_def.get("label", prop_name))
                        label.set_xalign(0)
                        label.set_halign(Gtk.Align.START)
                        row.pack_start(label, True, True, 0)

                        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                        controls.set_halign(Gtk.Align.END)
                        try:
                            widget = create_property_widget(prop_def, prop_name, theme_path, css_filename=css_filename)
                        except Exception as e:
                            print(f"Error creating widget for {prop_name}: {e}")
                            widget = Gtk.Label(label="Error")
                        controls.pack_start(widget, False, False, 0)

                        row.pack_start(controls, False, False, 0)
                        section_box.pack_start(row, False, False, 0)

                    widget_box.pack_start(section_expander, False, False, 0)

            states = widget_data.get("states", {})
            if states:
                states_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                for state_name in states.keys():
                    state_label = Gtk.Label(label=state_name.capitalize())
                    state_label.set_xalign(0)
                    states_box.pack_start(state_label, False, False, 0)
                widget_box.pack_start(states_box, False, False, 0)

    scrolled.show_all()
    return scrolled


def _read_xfwm4_themerc(theme_path):
    xfwm_dir = Path(theme_path) / "xfwm4"
    config_path = xfwm_dir / "themerc"
    config = {}

    if not config_path.exists():
        return config

    for raw_line in config_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        config[key.strip()] = value.strip()

    return config


def _write_xfwm4_themerc(theme_name, key, value):
    theme_path = find_gtk_theme_path(theme_name)
    if theme_path is None:
        return False

    temp_root = Path.home() / ".xfce-theme-studio" / "theme"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_theme = temp_root / f"{theme_name}.temp"

    if not temp_theme.exists():
        shutil.copytree(theme_path, temp_theme, dirs_exist_ok=True)

    xfwm_dir = temp_theme / "xfwm4"
    themerc_path = xfwm_dir / "themerc"
    themerc_path.parent.mkdir(parents=True, exist_ok=True)

    config = _read_xfwm4_themerc(str(temp_theme))
    config[key] = value

    lines = []
    for existing_key in sorted(config.keys()):
        lines.append(f"{existing_key}={config[existing_key]}")

    themerc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _xfwm4_widget_label(key):
    labels = {
        "active_text_color": "Active title text color",
        "inactive_text_color": "Inactive title text color",
        "active_text_shadow_color": "Active title shadow color",
        "inactive_text_shadow_color": "Inactive title shadow color",
        "title_shadow_active": "Active title shadow",
        "title_shadow_inactive": "Inactive title shadow",
        "full_width_title": "Full-width title bar",
        "button_offset": "Button offset",
        "button_spacing": "Button spacing",
        "shadow_delta_x": "Shadow offset X",
        "shadow_delta_y": "Shadow offset Y",
        "shadow_delta_width": "Shadow width",
        "shadow_delta_height": "Shadow height",
        "shadow_opacity": "Shadow opacity",
        "show_app_icon": "Show app icon",
        "show_popup_shadow": "Show popup shadow",
    }
    return labels.get(key, key.replace("_", " ").capitalize())


def _xfwm4_button_label(button_name, state):
    friendly_names = {
        "close": "Close button",
        "maximize": "Maximize button",
        "hide": "Hide button",
        "shade": "Shade button",
        "stick": "Stick button",
        "menu": "Menu button",
    }
    state_labels = {
        "active": "active",
        "inactive": "inactive",
        "prelight": "hover",
        "pressed": "pressed",
        "toggled-active": "toggled active",
        "toggled-inactive": "toggled inactive",
        "toggled-prelight": "toggled hover",
        "toggled-pressed": "toggled pressed",
    }
    return f"{friendly_names.get(button_name, button_name.title())} — {state_labels.get(state, state.replace('-', ' '))}"


def _create_xfwm4_value_widget(key, value):
    if key.endswith("_color"):
        button = Gtk.ColorButton()
        try:
            rgba = Gdk.RGBA()
            if value:
                rgba.parse(str(value))
                button.set_rgba(rgba)
        except Exception:
            pass
        return button

    if key in ("title_shadow_active", "title_shadow_inactive", "full_width_title", "show_app_icon", "show_popup_shadow"):
        switch = Gtk.Switch()
        switch.set_active(str(value).lower() in ("true", "1", "yes", "on"))
        return switch

    if key in (
        "button_offset", "button_spacing",
        "shadow_delta_x", "shadow_delta_y", "shadow_delta_width", "shadow_delta_height",
        "shadow_opacity", "title_vertical_offset_active", "title_vertical_offset_inactive"
    ):
        adj = Gtk.Adjustment(float(value) if value not in (None, "") else 0, -100, 100, 1, 10, 0)
        spin = Gtk.SpinButton(adjustment=adj, digits=0)
        return spin

    if key in ("active_text_color", "inactive_text_color"):
        button = Gtk.ColorButton()
        try:
            rgba = Gdk.RGBA()
            if value:
                rgba.parse(str(value))
                button.set_rgba(rgba)
        except Exception:
            pass
        return button

    entry = Gtk.Entry()
    entry.set_text(str(value or ""))
    return entry


def _get_xfwm4_widget_value(widget, key):
    if isinstance(widget, Gtk.ColorButton):
        rgba = widget.get_rgba()
        return rgba.to_string()
    if isinstance(widget, Gtk.Switch):
        return "true" if widget.get_active() else "false"
    if isinstance(widget, Gtk.SpinButton):
        return str(int(widget.get_value()))
    if isinstance(widget, Gtk.Entry):
        return widget.get_text().strip()
    return str(widget)


def _xfwm4_image_pixels(image_path):
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(image_path))
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        rowstride = pixbuf.get_rowstride()
        channels = pixbuf.get_n_channels()
        raw_pixels = pixbuf.get_pixels()
        pixels = []

        for y in range(height):
            row_start = y * rowstride
            for x in range(width):
                offset = row_start + (x * channels)
                red = raw_pixels[offset]
                green = raw_pixels[offset + 1]
                blue = raw_pixels[offset + 2]
                alpha = raw_pixels[offset + 3] if channels == 4 else 255
                pixels.append((red, green, blue, alpha))

        return width, height, pixels
    except Exception:
        return None


def _xfwm4_average_nontransparent_color(image_path):
    image_data = _xfwm4_image_pixels(image_path)
    if image_data is None:
        return None

    _, _, pixels = image_data
    opaque_pixels = [pixel for pixel in pixels if pixel[3] > 8]
    if not opaque_pixels:
        return None

    total_weight = sum(max(pixel[3], 1) for pixel in opaque_pixels)
    return tuple(
        int(sum(pixel[index] * max(pixel[3], 1) for pixel in opaque_pixels) / total_weight)
        for index in range(3)
    )


def _xfwm4_strip_thickness(image_path, orientation):
    image_data = _xfwm4_image_pixels(image_path)
    if image_data is None:
        return 0

    width, height, pixels = image_data
    if orientation == "vertical":
        strip_values = range(width)
        value_size = width
        get_alpha = lambda value: max(
            pixels[(row * width) + value][3] for row in range(height)
        )
    else:
        strip_values = range(height)
        value_size = height
        get_alpha = lambda value: max(
            pixels[(value * width) + column][3] for column in range(width)
        )

    occupied = [value for value in strip_values if get_alpha(value) > 8]
    if not occupied:
        return 0
    return occupied[-1] - occupied[0] + 1


def _xfwm4_extract_theme_materials(theme_path):
    xfwm_dir = Path(theme_path) / "xfwm4"
    if not xfwm_dir.exists():
        return {
            "background_color": None,
            "border_color": None,
            "border_width": 0,
        }

    active_files = sorted(xfwm_dir.glob("*.png"))
    border_candidates = [
        path for path in active_files
        if path.name.endswith("-active.png")
        and path.name.startswith(("left-", "right-", "top-", "bottom-"))
    ]
    background_candidates = [
        path for path in active_files
        if path.name.endswith("-active.png") and path.name.startswith("title-")
    ]

    if not border_candidates:
        border_candidates = [
            path for path in active_files
            if path.name.startswith(("left-", "right-", "top-", "bottom-"))
        ]
    if not background_candidates:
        background_candidates = [path for path in active_files if path.name.startswith("title-")]

    border_color = None
    background_color = None
    border_width = 0

    def average_colors(paths):
        values = []
        for path in paths:
            color = _xfwm4_average_nontransparent_color(str(path))
            if color is not None:
                values.append(color)
        if not values:
            return None
        total_r = sum(v[0] for v in values)
        total_g = sum(v[1] for v in values)
        total_b = sum(v[2] for v in values)
        count = len(values)
        return (int(total_r / count), int(total_g / count), int(total_b / count))

    def count_colors(paths):
        color_counts = {}
        for path in paths:
            try:
                with Image.open(path) as source:
                    pixels = source.convert("RGBA").getdata()
            except Exception:
                continue
            for red, green, blue, alpha in pixels:
                if alpha > 8:
                    color = (red, green, blue)
                    color_counts[color] = color_counts.get(color, 0) + 1
        return color_counts

    def dominant_color(paths):
        counts = count_colors(paths)
        if not counts:
            return None
        return max(counts, key=counts.get)

    background_color = average_colors(background_candidates)
    border_color = dominant_color(border_candidates)
    if border_color and background_color:
        border_counts = count_colors(border_candidates)
        distinct_border_colors = {
            color: count for color, count in border_counts.items()
            if sum((color[index] - background_color[index]) ** 2 for index in range(3)) > 24 * 24
        }
        if distinct_border_colors:
            border_color = max(distinct_border_colors, key=distinct_border_colors.get)
    if border_color is None:
        border_color = average_colors(border_candidates)

    width_candidates = []
    for path in border_candidates:
        name = path.name
        orientation = "vertical" if name.startswith(("left-", "right-")) else "horizontal"
        thickness = _xfwm4_strip_thickness(path, orientation)
        if thickness:
            width_candidates.append(thickness)
    if width_candidates:
        border_width = max(set(width_candidates), key=width_candidates.count)

    return {
        "background_color": background_color,
        "border_color": border_color,
        "border_width": border_width,
    }

def _xfwm4_prepare_asset_pixbuf(image_path, materials, target_path):
    try:
        with Image.open(image_path) as source:
            logo = source.convert("RGBA")
        with Image.open(target_path) as source_template:
            template = source_template.convert("RGBA")
            width, height = template.size

            background = materials.get("background_color")
            border = materials.get("border_color")
            background = tuple(background or (0, 0, 0))
            border = tuple(border) if border else None
            old_border = materials.get("source_border_color")
            tolerance_squared = 48 * 48

            canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            canvas_pixels = canvas.load()
            template_pixels = template.load()

            for y in range(height):
                for x in range(width):
                    red, green, blue, alpha = template_pixels[x, y]
                    if alpha == 0:
                        continue
                    is_border = bool(
                        old_border
                        and (red - old_border[0]) ** 2
                        + (green - old_border[1]) ** 2
                        + (blue - old_border[2]) ** 2
                        <= tolerance_squared
                    )
                    if is_border and border:
                        canvas_pixels[x, y] = (*border, alpha)
                    else:
                        canvas_pixels[x, y] = (*background, alpha)

            logo_size = max(1, min(16, width, height))
            logo.thumbnail((logo_size, logo_size), Image.LANCZOS)
            logo_x = (width - logo.width) // 2
            logo_y = (height - logo.height) // 2
            canvas.alpha_composite(logo, (logo_x, logo_y))

            raw_data = canvas.tobytes()
            return GdkPixbuf.Pixbuf.new_from_data(
                raw_data,
                GdkPixbuf.Colorspace.RGB,
                True,
                8,
                width,
                height,
                width * 4,
                None,
            )
    except Exception:
        return None

def _xfwm4_replace_theme_color(theme_path, old_color, new_color):
    if not old_color or not new_color:
        return False

    theme_name = Path(theme_path).name
    if theme_name.endswith(".temp"):
        theme_name = theme_name[:-5]

    temp_root = Path.home() / ".xfce-theme-studio" / "theme"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_theme = temp_root / f"{theme_name}.temp"
    if not temp_theme.exists():
        shutil.copytree(theme_path, temp_theme, dirs_exist_ok=True)

    xfwm_dir = temp_theme / "xfwm4"
    if not xfwm_dir.exists():
        return False

    tolerance_squared = 32 * 32
    changed = False
    for image_path in xfwm_dir.glob("*.png"):
        try:
            with Image.open(image_path) as source:
                image = source.convert("RGBA")
                pixels = image.load()
                image_changed = False

                for y in range(image.height):
                    for x in range(image.width):
                        red, green, blue, alpha = pixels[x, y]
                        if alpha == 0:
                            continue
                        distance_squared = (
                            (red - old_color[0]) ** 2
                            + (green - old_color[1]) ** 2
                            + (blue - old_color[2]) ** 2
                        )
                        if distance_squared <= tolerance_squared:
                            pixels[x, y] = (*new_color, alpha)
                            image_changed = True

                if image_changed:
                    image.save(image_path, format="PNG")
                    changed = True
        except Exception:
            continue

    return changed


def _xfwm4_replace_background_color(theme_path, old_color, new_color):
    return _xfwm4_replace_theme_color(theme_path, old_color, new_color)


def _xfwm4_replace_border_color(theme_path, old_color, new_color):
    return _xfwm4_replace_theme_color(theme_path, old_color, new_color)


def _xfwm4_color_to_hex(color):
    if not color:
        return "unknown"
    return "#%02x%02x%02x" % tuple(color)


def _build_xfwm4_tab_content(theme_path):
    xfwm_dir = Path(theme_path) / "xfwm4"
    root = Gtk.ScrolledWindow()
    root.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    root.set_hexpand(True)
    root.set_vexpand(True)

    if not xfwm_dir.exists():
        msg = Gtk.Label(label="No xfwm4 folder found in this theme.")
        msg.set_xalign(0)
        root.add(msg)
        return root

    config = _read_xfwm4_themerc(theme_path)
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=8)
    content.set_hexpand(True)
    content.set_vexpand(True)

    settings_frame = Gtk.Frame(label="XFWM4 settings")
    settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=8)
    settings_frame.add(settings_box)
    content.pack_start(settings_frame, False, False, 0)

    materials = _xfwm4_extract_theme_materials(theme_path)

    if not config:
        settings_box.pack_start(Gtk.Label(label="No themerc settings found in this theme."), False, False, 0)
    else:
        visible_keys = [
            "active_text_color",
            "inactive_text_color",
            "active_text_shadow_color",
            "inactive_text_shadow_color",
            "title_shadow_active",
            "title_shadow_inactive",
            "full_width_title",
            "button_offset",
            "button_spacing",
            "shadow_delta_x",
            "shadow_delta_y",
            "shadow_delta_width",
            "shadow_delta_height",
            "shadow_opacity",
            "show_app_icon",
            "show_popup_shadow",
        ]

        settings_grid = Gtk.Grid(row_spacing=6, column_spacing=10)
        settings_grid.set_hexpand(True)
        background_color_state = {
            "value": materials.get("background_color"),
        }
        border_color_state = {
            "value": materials.get("border_color"),
        }

        def refresh_preview_images():
            theme_name = Path(theme_path).name
            if theme_name.endswith(".temp"):
                theme_name = theme_name[:-5]
            temp_xfwm_dir = (
                Path.home()
                / ".xfce-theme-studio"
                / "theme"
                / f"{theme_name}.temp"
                / "xfwm4"
            )
            for image_widget, image_name in preview_images:
                updated_image = temp_xfwm_dir / image_name
                if updated_image.exists():
                    image_widget.set_from_file(str(updated_image))

        settings_row = 0

        window_settings = [
            ("Background color", "background_color", "color"),
            ("Border color", "border_color", "color"),
        ]

        for label_text, material_key, value_type in window_settings:
            label = Gtk.Label(label=label_text)
            label.set_xalign(0)
            label.set_hexpand(True)

            if value_type == "color":
                color_button = Gtk.ColorButton()
                color_value = materials.get(material_key)
                if color_value:
                    rgba = Gdk.RGBA()
                    rgba.parse("#%02x%02x%02x" % tuple(color_value))
                    color_button.set_rgba(rgba)
                if material_key in ("background_color", "border_color"):
                    def on_material_color_set(button, current_key=material_key):
                        rgba = button.get_rgba()
                        new_color = (
                            round(rgba.red * 255),
                            round(rgba.green * 255),
                            round(rgba.blue * 255),
                        )
                        color_state = (
                            background_color_state
                            if current_key == "background_color"
                            else border_color_state
                        )
                        old_color = color_state["value"]
                        if _xfwm4_replace_theme_color(theme_path, old_color, new_color):
                            color_state["value"] = new_color
                            refresh_preview_images()

                    color_button.connect("color-set", on_material_color_set)
                widget = color_button
            else:
                adj = Gtk.Adjustment(float(materials.get(material_key, 0) or 0), 0, 100, 1, 10, 0)
                widget = Gtk.SpinButton(adjustment=adj, digits=0)

            settings_grid.attach(label, 0, settings_row, 1, 1)
            settings_grid.attach(widget, 1, settings_row, 1, 1)
            settings_row += 1

        for key in visible_keys:
            if key not in config:
                continue

            label = Gtk.Label(label=_xfwm4_widget_label(key))
            label.set_xalign(0)
            label.set_hexpand(True)
            widget = _create_xfwm4_value_widget(key, config[key])
            widget.set_hexpand(False)

            def make_commit_callback(current_key, current_widget):
                def on_change(_widget=None, *_args):
                    value = _get_xfwm4_widget_value(current_widget, current_key)
                    theme_name = Path(theme_path).name
                    if theme_name.endswith(".temp"):
                        theme_name = theme_name[:-5]
                    _write_xfwm4_themerc(theme_name, current_key, value)
                return on_change

            if isinstance(widget, Gtk.ColorButton):
                widget.connect("color-set", make_commit_callback(key, widget))
            elif isinstance(widget, Gtk.Switch):
                widget.connect("notify::active", make_commit_callback(key, widget))
            elif isinstance(widget, Gtk.SpinButton):
                widget.connect("value-changed", make_commit_callback(key, widget))
            else:
                widget.connect("changed", make_commit_callback(key, widget))

            settings_grid.attach(label, 0, settings_row, 1, 1)
            settings_grid.attach(widget, 1, settings_row, 1, 1)
            settings_row += 1

        if settings_row == 0:
            settings_box.pack_start(Gtk.Label(label="The themerc is present, but no commonly used fields were detected."), False, False, 0)
        else:
            settings_box.pack_start(settings_grid, False, False, 0)

    preview_frame = Gtk.Frame(label="Window control preview")
    preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=8)
    preview_frame.add(preview_box)

    selection_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    selection_bar.set_hexpand(True)
    selection_label = Gtk.Label(label="Selected item: none")
    selection_label.set_xalign(0)
    selection_bar.pack_start(selection_label, True, True, 0)

    change_image_button = Gtk.Button(label="Change image")
    selection_bar.pack_start(change_image_button, False, False, 0)
    preview_box.pack_start(selection_bar, False, False, 0)

    button_groups = [
        ("close", ["active", "inactive", "prelight", "pressed"]),
        ("maximize", ["active", "inactive", "prelight", "pressed", "toggled-active", "toggled-inactive", "toggled-prelight", "toggled-pressed"]),
        ("hide", ["active", "inactive", "prelight", "pressed"]),
        ("shade", ["active", "inactive", "prelight", "pressed", "toggled-active", "toggled-inactive", "toggled-prelight", "toggled-pressed"]),
        ("stick", ["active", "inactive", "prelight", "pressed", "toggled-active", "toggled-inactive", "toggled-prelight", "toggled-pressed"]),
        ("menu", ["active", "inactive", "prelight", "pressed"]),
    ]

    preview_grid = Gtk.Grid(row_spacing=8, column_spacing=10)
    preview_grid.set_column_homogeneous(False)
    preview_grid.set_row_homogeneous(False)
    position = 0
    preview_images = []
    selected_asset = {"widget": None, "image_widget": None, "label": None, "filename": None}

    def select_asset(asset_name, button_widget, image_widget=None, filename=None):
        if selected_asset["widget"] and selected_asset["widget"] is not button_widget:
            old_widget = selected_asset["widget"]
            old_widget.set_state_flags(Gtk.StateFlags.NORMAL, True)
            old_widget.get_style_context().remove_class("icon-cell-selected")

        selected_asset["widget"] = button_widget
        selected_asset["image_widget"] = image_widget
        selected_asset["label"] = asset_name
        selected_asset["filename"] = filename
        button_widget.set_state_flags(Gtk.StateFlags.SELECTED, True)
        button_widget.get_style_context().add_class("icon-cell-selected")
        selection_label.set_text(f"Selected item: {asset_name}")
        change_image_button.set_sensitive(True)

    def on_change_image():
        if selected_asset["widget"] is None or selected_asset["filename"] is None:
            return

        dialog = Gtk.FileChooserDialog(
            title="Choose an image",
            parent=None,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)

        filter_image = Gtk.FileFilter()
        filter_image.set_name("Image files")
        filter_image.add_mime_type("image/png")
        filter_image.add_mime_type("image/jpeg")
        filter_image.add_mime_type("image/svg+xml")
        filter_image.add_pattern("*.png")
        filter_image.add_pattern("*.jpg")
        filter_image.add_pattern("*.jpeg")
        filter_image.add_pattern("*.svg")
        dialog.add_filter(filter_image)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            if path:
                try:
                    target_path = xfwm_dir / selected_asset["filename"]
                    source_pixbuf = _xfwm4_prepare_asset_pixbuf(
                        path,
                        {
                            "background_color": background_color_state["value"],
                            "border_color": border_color_state["value"],
                            "source_border_color": materials.get("border_color"),
                        },
                        str(target_path),
                    )
                    if source_pixbuf is None:
                        raise ValueError("The selected image could not be processed")

                    theme_name = Path(theme_path).name
                    if theme_name.endswith(".temp"):
                        theme_name = theme_name[:-5]
                    temp_theme = Path.home() / ".xfce-theme-studio" / "theme" / f"{theme_name}.temp"
                    if not temp_theme.exists():
                        shutil.copytree(theme_path, temp_theme, dirs_exist_ok=True)
                    destination = temp_theme / "xfwm4" / selected_asset["filename"]
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    source_pixbuf.savev(str(destination), "png", [], [])

                    scaled = source_pixbuf.scale_simple(28, 28, GdkPixbuf.InterpType.BILINEAR)
                    if selected_asset["image_widget"] is not None:
                        selected_asset["image_widget"].set_from_pixbuf(scaled)
                    refresh_preview_images()
                    selection_label.set_text(f"Selected item: {selected_asset['label']} (image updated)")
                except Exception:
                    selection_label.set_text(f"Selected item: {selected_asset['label']} (image update failed)")
        dialog.destroy()

    change_image_button.connect("clicked", lambda *_: on_change_image())

    for button_name, states in button_groups:
        for state in states:
            asset_name = f"{button_name}-{state}.png"
            asset_path = xfwm_dir / asset_name
            if not asset_path.exists():
                continue

            asset_button = Gtk.Button()
            asset_button.set_relief(Gtk.ReliefStyle.NONE)
            asset_button.set_focus_on_click(True)
            asset_button.set_hexpand(False)
            asset_button.set_vexpand(False)
            asset_button.get_style_context().add_class("xfwm4-asset-button")
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            img = Gtk.Image.new_from_file(str(asset_path))
            img.set_pixel_size(28)
            img.set_halign(Gtk.Align.CENTER)
            label = Gtk.Label(label=_xfwm4_button_label(button_name, state))
            label.set_line_wrap(True)
            label.set_justify(Gtk.Justification.CENTER)
            label.set_xalign(0.5)
            preview_images.append((img, asset_name))
            outer.pack_start(img, True, True, 0)
            outer.pack_start(label, False, False, 0)
            asset_button.add(outer)

            asset_button.connect(
                "clicked",
                lambda _btn, name=_xfwm4_button_label(button_name, state), img_widget=img, filename=asset_name:
                    select_asset(name, _btn, img_widget, filename),
            )

            col = position % 4
            row = position // 4
            preview_grid.attach(asset_button, col, row, 1, 1)
            position += 1

    if position == 0:
        preview_grid.attach(Gtk.Label(label="No usable XFWM4 button assets were found."), 0, 0, 1, 1)

    preview_box.pack_start(preview_grid, True, True, 0)
    content.pack_start(preview_frame, True, True, 0)
    root.add(content)
    return root


def build_gtk_theme_ui(container, theme_path, theme_structure=THEME_STRUCTURE):
    clear_container(container)

    # Create a notebook with 3 tabs
    notebook = Gtk.Notebook()
    notebook.set_hexpand(True)
    notebook.set_vexpand(True)
    container.pack_start(notebook, True, True, 0)

    # Tab 1: Light Theme (gtk.css)
    gtk_css_content = _build_css_tab_content(theme_path, "gtk.css", theme_structure)
    tab1_label = Gtk.Label(label="Light Theme")
    notebook.append_page(gtk_css_content, tab1_label)

    # Tab 2: Dark Theme (gtk-dark.css)
    gtk_dark_css_content = _build_css_tab_content(theme_path, "gtk-dark.css", theme_structure)
    tab2_label = Gtk.Label(label="Dark Theme")
    notebook.append_page(gtk_dark_css_content, tab2_label)

    # Tab 3: Window Manager (xfwm4)
    xfwm4_content = _build_xfwm4_tab_content(theme_path)
    tab3_label = Gtk.Label(label="Window Borders")
    notebook.append_page(xfwm4_content, tab3_label)

    container.show_all()


def delete_gtk_theme_popup(parent, theme_listbox):
    _, custom = list_gtk_themes()

    if not custom:
        dialog = Gtk.MessageDialog(parent, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, "No custom GTK themes to delete.")
        dialog.run()
        dialog.destroy()
        return

    popup = Gtk.Window()
    popup.set_title("Delete GTK/XFWM4 Theme")
    popup.set_default_size(375, 250)
    popup.set_resizable(False)
    popup.set_transient_for(parent)
    popup.set_modal(True)

    selected_theme = {"value": ""}

    main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    main_box.set_margin_start(10)
    main_box.set_margin_end(10)
    main_box.set_margin_top(10)
    main_box.set_margin_bottom(10)
    popup.add(main_box)

    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    main_box.pack_start(left, True, True, 0)

    search_entry = Gtk.Entry()
    search_entry.set_placeholder_text("Search...")
    left.pack_start(search_entry, False, False, 0)

    listbox_frame = Gtk.Frame()
    left.pack_start(listbox_frame, True, True, 0)

    theme_store = Gtk.ListStore(str)
    listbox = Gtk.TreeView(model=theme_store)
    listbox.set_headers_visible(False)
    renderer = Gtk.CellRendererText()
    column = Gtk.TreeViewColumn("Theme", renderer, text=0)
    listbox.append_column(column)

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.add(listbox)
    listbox_frame.add(scrolled)

    right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    main_box.pack_start(right, True, True, 0)

    lbl_selected = Gtk.Label(label="Selected Theme:")
    lbl_selected.set_alignment(0, 0.5)
    right.pack_start(lbl_selected, False, False, 0)

    theme_label = Gtk.Label(label="None")
    theme_label.set_alignment(0, 0.5)
    right.pack_start(theme_label, False, False, 0)

    lbl_confirm = Gtk.Label(label="Theme name to confirm:")
    lbl_confirm.set_alignment(0, 0.5)
    right.pack_start(lbl_confirm, False, False, 0)

    name_entry = Gtk.Entry()
    right.pack_start(name_entry, False, False, 0)

    btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    right.pack_end(btn_box, False, False, 0)

    def refresh():
        q = search_entry.get_text().lower()
        theme_store.clear()
        theme_store.append(["—— Custom Themes ——"])
        for t in custom:
            if q in t.lower():
                theme_store.append([t])

    def on_select(selection):
        model, treeiter = selection.get_selected()
        if not treeiter:
            return
        val = model.get_value(treeiter, 0)
        if val.startswith("——") or val == "":
            return
        selected_theme["value"] = val
        theme_label.set_text(val)

    selection = listbox.get_selection()
    selection.connect("changed", on_select)
    search_entry.connect("changed", lambda *args: refresh())
    refresh()

    def delete_theme():
        theme = selected_theme["value"]
        if not theme:
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Select a theme")
            dialog.run()
            dialog.destroy()
            return

        name_confirm = name_entry.get_text().strip()
        if name_confirm != theme:
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Name does not match")
            dialog.run()
            dialog.destroy()
            name_entry.set_text("")
            return

        path = os.path.join(GTK_USER_PATH, theme)
        try:
            shutil.rmtree(path)
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, f"Theme '{theme}' deleted")
            dialog.run()
            dialog.destroy()
            popup.destroy()
            refresh_gtk_theme_listbox(theme_listbox)
        except Exception as e:
            dialog = Gtk.MessageDialog(popup, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, f"Failed to delete: {e}")
            dialog.run()
            dialog.destroy()

    btn_delete = Gtk.Button(label="Delete")
    btn_delete.connect("clicked", lambda *args: delete_theme())
    btn_box.pack_start(btn_delete, True, True, 0)

    btn_cancel = Gtk.Button(label="Cancel")
    btn_cancel.connect("clicked", lambda *args: popup.destroy())
    btn_box.pack_start(btn_cancel, True, True, 0)

    popup.show_all()


def on_gtk_theme_select(event, theme_listbox, entry_name, details_label, ui_container=None):
    selection = theme_listbox.get_selection()
    if not selection:
        return
    model, treeiter = selection.get_selected()
    if not treeiter:
        return

    theme_name = model.get_value(treeiter, 0)
    entry_name.set_text(theme_name)
    path = find_gtk_theme_path(theme_name)
    details_label.set_text(
        f"Selected GTK/XFWM4 theme: {theme_name}\n"
        f"Path: {path or 'Not found'}\n"
        "Use the tools in the header to create/delete a GTK/XFWM4 theme."
    )
    if ui_container is not None:
        if not path==None:
            build_gtk_theme_ui(ui_container, path)


def save_gtk_theme(theme_name):
    # Copy any modifications from the temporary theme folder back to the original
    temp_path = Path(f"~/.xfce-theme-studio/theme/{theme_name}.temp").expanduser()

    # Find original theme path (prefer user theme)
    original = find_gtk_theme_path(theme_name)
    if not original:
        return f"Original GTK theme '{theme_name}' not found"

    original_path = Path(original)

    if not temp_path.exists():
        return f"No temporary changes to save for '{theme_name}'"

    try:
        # normalize temporary GTK CSS files so units are applied before final save
        temp_css_paths = get_gtk_css_paths(str(temp_path))
        for temp_css_path in temp_css_paths:
            try:
                with open(temp_css_path, "r", encoding="utf-8") as f:
                    css_text = f.read()
                with open(temp_css_path, "w", encoding="utf-8") as f:
                    f.write(_apply_units_on_save(css_text))
            except Exception:
                pass

        # copy, overwriting existing files
        for item in temp_path.rglob("*"):
            if item.is_file():
                dest = original_path / item.relative_to(temp_path)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)

        # remove the temp folder
        shutil.rmtree(temp_path)

        # mark modifications cleared
        try:
            from icon_modify import changeFalse
            changeFalse()
        except Exception:
            pass

        return f"GTK/XFWM4 theme '{theme_name}' saved."
    except Exception as e:
        return f"Failed to save GTK theme '{theme_name}': {e}"


def reset_gtk_theme(theme_name):
    return f"GTK reset is not implemented."


def get_theme_paths(theme_name):
    result = []
    visited = set()

    def resolve(name):
        if name in visited:
            return
        visited.add(name)

        path = find_theme_path(name)
        if not path:
            return

        result.append(path)

        index_file = os.path.join(path, "index.theme")
        if not os.path.exists(index_file):
            return

        config = configparser.ConfigParser()
        config.read(index_file)

        if "Icon Theme" not in config:
            return

        inherits = config["Icon Theme"].get("Inherits", "")

        for parent in [t.strip() for t in inherits.split(",") if t.strip()]:
            resolve(parent)

    resolve(theme_name)

    return result


def rename_theme(old_name, new_name):
    if old_name == new_name:
        return True, ""

    if not re.match(r"^[^/\\\\]+$", new_name):
        return False, "Invalid theme name"

    system, custom = list_themes()
    if new_name in system or new_name in custom:
        return False, "A theme with that name already exists"

    old_path = os.path.join(USER_PATH, old_name)
    new_path = os.path.join(USER_PATH, new_name)
    if not os.path.isdir(old_path):
        return False, "Original theme not found"

    try:
        os.rename(old_path, new_path)

        old_temp = Path.home() / ".xfce-theme-studio" / "theme" / f"{old_name}.temp"
        new_temp = Path.home() / ".xfce-theme-studio" / "theme" / f"{new_name}.temp"
        if old_temp.exists():
            old_temp.rename(new_temp)

        # Update index.theme by replacing only the Name line, preserving case
        index_file = os.path.join(new_path, "index.theme")
        if os.path.isfile(index_file):
            with open(index_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            with open(index_file, "w", encoding="utf-8") as f:
                for line in lines:
                    if line.startswith("Name="):
                        f.write(f"Name={new_name}\n")
                    else:
                        f.write(line)

        return True, ""
    except Exception as e:
        return False, f"Failed to rename theme: {e}"


def on_theme_select(event, theme_listbox, tabs, entry_name):
    """When clicking a theme in the listbox, update the tabs."""
    selection = theme_listbox.get_selection()
    if not selection:
        return
    model, treeiter = selection.get_selected()
    if not treeiter:
        return
    theme_name = model.get_value(treeiter, 0)

    # 🔹 Update the Entry Name
    entry_name.set_text(theme_name)

    # 🔹 retrieve theme paths + inheritance (includes temp folder)
    theme_dirs = get_theme_dirs_with_inheritance(theme_name)

    # 🔹 rebuild all icons for each tab
    for tab in tabs:
        tab.build_icons(theme_dirs)
        tab.current_theme_name = theme_name


##################################### save and reset ######################################

import shutil
from pathlib import Path
from icon_modify import changeFalse

def save_theme(theme_name):
    temp_path = Path(f"~/.xfce-theme-studio/theme/{theme_name}.temp").expanduser()
    final_path = Path(f"~/.local/share/icons/{theme_name}").expanduser()

    if not temp_path.exists():
        return

    # copy, overwriting existing files
    for item in temp_path.rglob("*"):
        if item.is_file():
            dest = final_path / item.relative_to(temp_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)

    # suppression du temp
    shutil.rmtree(temp_path)

    if shutil.which('gtk-update-icon-cache'):
        try:
            subprocess.run(
                ['gtk-update-icon-cache', '-f', str(final_path)],
                check=True
            )

        except subprocess.CalledProcessError as e:
            print(f"Failed to update icon cache: {e}")
    else:
        print("gtk-update-icon-cache not found")

    changeFalse()


def reset_theme(theme_name):
    temp_path = Path(f"~/.xfce-theme-studio/theme/{theme_name}.temp").expanduser()

    if temp_path.exists():
        shutil.rmtree(temp_path)
    changeFalse()

