import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
import os
import subprocess
import re
import random
import shutil
import configparser
from pathlib import Path
from theme_structure import THEME_STRUCTURE
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
    xfwm4_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=6)
    xfwm4_label = Gtk.Label()
    xfwm4_label.set_markup("<i>Window Manager icons grid coming soon...</i>")
    xfwm4_label.set_alignment(0.5, 0.5)
    xfwm4_box.pack_start(xfwm4_label, True, True, 0)
    tab3_label = Gtk.Label(label="Window Borders")
    notebook.append_page(xfwm4_box, tab3_label)

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

