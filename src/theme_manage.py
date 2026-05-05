import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import os
import subprocess
import re
import random
import shutil
import configparser
from pathlib import Path

SYSTEM_PATH = "/usr/share/icons"
USER_PATH = os.path.expanduser("~/.local/share/icons")
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
        
        # Read index.theme for Inherits
        index_path = os.path.join(USER_PATH, current, "index.theme")
        if not os.path.exists(index_path):
            index_path = os.path.join(SYSTEM_PATH, current, "index.theme")
        
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
                # en-tête
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
    _, custom = list_themes()  # on ne prend que les thèmes custom

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

################## mettre à jour le theme selectionné ####################


def find_theme_path(name):
    # priorité au custom
    local = os.path.join(USER_PATH, name)
    if os.path.isdir(local):
        return local

    system = os.path.join(SYSTEM_PATH, name)
    if os.path.isdir(system):
        return system

    return None


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
    """Quand on clique sur un thème dans la listbox, met à jour les onglets."""
    selection = theme_listbox.get_selection()
    if not selection:
        return
    model, treeiter = selection.get_selected()
    if not treeiter:
        return
    theme_name = model.get_value(treeiter, 0)

    # 🔹 Mettre à jour l'Entry Name
    entry_name.set_text(theme_name)

    # 🔹 récupérer les chemins du thème + héritage (inclut le dossier temp)
    theme_dirs = get_theme_dirs_with_inheritance(theme_name)

    # 🔹 reconstruire toutes les icônes pour chaque onglet
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

    # copie en écrasant
    for item in temp_path.rglob("*"):
        if item.is_file():
            dest = final_path / item.relative_to(temp_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)

    # suppression du temp
    shutil.rmtree(temp_path)

    print(f"Updating icon cache for theme: {theme_name} at {final_path}")

    if shutil.which('gtk-update-icon-cache'):
        try:
            subprocess.run(
                ['gtk-update-icon-cache', '-f', str(final_path)],
                check=True
            )
            print(f"Icon cache updated successfully for theme {theme_name}")

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






















    
