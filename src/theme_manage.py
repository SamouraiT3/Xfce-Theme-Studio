import tkinter as tk
from tkinter import messagebox
import os
import re
import random
import configparser

SYSTEM_PATH = "/usr/share/icons"
USER_PATH = os.path.expanduser("~/.local/share/icons")
CATEGORIES = ["apps", "places", "devices", "actions", "status"]
CONTEXTS = {
    "apps": "Applications",
    "places": "Places",
    "devices": "Devices",
    "actions": "Actions",
    "status": "Status"
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
    current = theme_name
    while current and current not in visited:
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
                current = inherits[0] if inherits else None
            else:
                current = None
        else:
            current = None
    return dirs

############################################ create theme ###############################################

def create_theme_popup(parent, theme_listbox):
    system, custom = list_themes()

    popup = tk.Toplevel(parent)
    popup.title("Create Theme")
    popup.geometry("375x250")
    popup.resizable(False, False)  # ❌ non redimensionnable

    selected_theme = tk.StringVar()
    name_var = tk.StringVar()
    search_var = tk.StringVar()

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

    left = tk.Frame(popup)
    left.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    tk.Entry(left, textvariable=search_var).pack(fill="x", pady=(0,5))

    listbox_frame = tk.Frame(left)
    listbox_frame.pack(fill="both", expand=True)

    scrollbar = tk.Scrollbar(listbox_frame)
    scrollbar.pack(side="right", fill="y")

    listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set)
    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=listbox.yview)

    def refresh():
        q = search_var.get().lower()
        listbox.delete(0, "end")

        listbox.insert("end", "—— System Themes ——")
        for t in system:
            if q in t.lower():
                listbox.insert("end", t)

        listbox.insert("end", "")
        listbox.insert("end", "—— Custom Themes ——")
        for t in custom:
            if q in t.lower():
                listbox.insert("end", t)

    search_var.trace_add("write", lambda *args: refresh())
    refresh()

    right = tk.Frame(popup)
    right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    tk.Label(right, text="Base Theme").pack(anchor="w")
    base_label = tk.Label(right, text="None")
    base_label.pack(anchor="w", pady=(0, 10))

    tk.Label(right, text="Theme Name").pack(anchor="w")
    tk.Entry(right, textvariable=name_var).pack(fill="x", pady=(0,10))

    def on_select(event):
        if not listbox.curselection():
            return
        val = listbox.get(listbox.curselection())
        if val.startswith("—") or val == "":
            return
        selected_theme.set(val)
        base_label.config(text=val)
        name_var.set(generate_name(val))

    listbox.bind("<<ListboxSelect>>", on_select)

    # -------- ACTIONS --------

    btn_frame = tk.Frame(right)
    btn_frame.pack(side="bottom", fill="x", pady=10)

    def create():
        base = selected_theme.get()
        name = name_var.get().strip()

        if not base:
            return messagebox.showerror("Error", "Select a base theme")
        if not name:
            return messagebox.showerror("Error", "Invalid name")
        if name in system or name in custom:
            return messagebox.showerror("Error", "Theme already exists")
        if not re.match(r"^[^/\\]+$", name):
            return messagebox.showerror("Error", "Invalid characters")

        path = os.path.join(USER_PATH, name)
        os.makedirs(path, exist_ok=True)

        inherits = read_inherits(base)
        final_inherits = [base] + [i for i in inherits if i != base]

        for cat in CATEGORIES:
            os.makedirs(os.path.join(path, cat), exist_ok=True)

        with open(os.path.join(path, "index.theme"), "w", encoding="utf-8") as f:
            # en-tête
            f.write("[Icon Theme]\n")
            f.write(f"Name={name}\n")
            f.write(f"Inherits={','.join(final_inherits)}\n")
            f.write(f"Directories={','.join(CATEGORIES)}\n\n")
    
            # sections automatiques
            for cat in CATEGORIES:
                f.write(f"[{cat}]\n")
                f.write(f"Size=64\n")
                f.write(f"Context={CONTEXTS[cat]}\n")
                f.write("Type=Fixed\n\n")

        messagebox.showinfo("Success", "Theme created")
        popup.destroy()
        refresh_theme_listbox(theme_listbox)

    tk.Button(btn_frame, text="Create", command=create, bg="#28a745", fg="white").pack(expand=True, fill="x", padx=5)
    tk.Button(btn_frame, text="Cancel", command=popup.destroy, bg="#555555", fg="white").pack(expand=True, fill="x", padx=5)


################################ delete theme ####################################
    
def delete_theme_popup(parent, theme_listbox):
    _, custom = list_themes()  # on ne prend que les thèmes custom

    if not custom:
        messagebox.showinfo("Info", "No custom themes to delete.")
        return

    popup = tk.Toplevel(parent)
    popup.title("Delete Theme")
    popup.geometry("375x250")
    popup.resizable(False, False)

    selected_theme = tk.StringVar()
    search_var = tk.StringVar()

    # -------- UI --------

    left = tk.Frame(popup)
    left.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    tk.Entry(left, textvariable=search_var).pack(fill="x", pady=(0,5))

    listbox_frame = tk.Frame(left)
    listbox_frame.pack(fill="both", expand=True)

    scrollbar = tk.Scrollbar(listbox_frame)
    scrollbar.pack(side="right", fill="y")

    listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set)
    listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=listbox.yview)

    def refresh():
        q = search_var.get().lower()
        listbox.delete(0, "end")

        listbox.insert("end", "—— Custom Themes ——")
        for t in custom:
            if q in t.lower():
                listbox.insert("end", t)

    search_var.trace_add("write", lambda *args: refresh())
    refresh()

    def on_select(event):
        if not listbox.curselection():
            return
        val = listbox.get(listbox.curselection())
        if val.startswith("—") or val == "":
            return
        selected_theme.set(val)

    listbox.bind("<<ListboxSelect>>", on_select)

    # -------- CONFIRMATION & ACTIONS --------

    right = tk.Frame(popup)
    right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    tk.Label(right, text="Selected Theme").pack(anchor="w")
    theme_label = tk.Label(right, text="None")
    theme_label.pack(anchor="w", pady=(0, 10))

    def update_label(*args):
        theme_label.config(text=selected_theme.get())

    selected_theme.trace_add("write", update_label)

    name_var = tk.StringVar()

    tk.Label(right, text="Theme name to confirm").pack(anchor="w")
    tk.Entry(right, textvariable=name_var).pack(fill="x", pady=(0,10))

    btn_frame = tk.Frame(right)
    btn_frame.pack(side="bottom", fill="x", pady=10)

    def delete():
        theme = selected_theme.get()
        if not theme:
            return messagebox.showerror("Error", "Select a theme")

        name_confirm = name_var.get().strip()
        if name_confirm != theme:
            messagebox.showerror("Error", "Name does not match")
            name_var.set("")
            return

        path = os.path.join(USER_PATH, theme)
        try:
            import shutil
            shutil.rmtree(path)
            messagebox.showinfo("Success", f"Theme '{theme}' deleted")
            popup.destroy()
            refresh_theme_listbox(theme_listbox)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

    tk.Button(btn_frame, text="Delete", command=delete, bg="#dc3545", fg="white").pack(expand=True, fill="x", padx=5)
    tk.Button(btn_frame, text="Cancel", command=popup.destroy, bg="#555555", fg="white").pack(expand=True, fill="x", padx=5)

########################## refresh listbox #############################

def refresh_theme_listbox(theme_listbox) :
    _, theme_list = list_themes()
    theme_listbox.delete(0, tk.END)
    for theme in theme_list :
        theme_listbox.insert(tk.END, theme)

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


def on_theme_select(event, theme_listbox, tabs, entry_name):
    """Quand on clique sur un thème dans la listbox, met à jour les onglets."""
    selection = theme_listbox.curselection()
    if not selection:
        return
    theme_name = theme_listbox.get(selection[0])

    # 🔹 Mettre à jour l'Entry Name
    entry_name.delete(0, tk.END)
    entry_name.insert(0, theme_name)

    # 🔹 récupérer les chemins du thème + héritage
    theme_dirs = get_theme_paths(theme_name)

    # 🔹 reconstruire toutes les icônes pour chaque onglet
    for tab in tabs:
        tab.build_icons(theme_dirs)
        tab.current_theme_name = theme_name


##################################### save and reset ######################################

import shutil
from pathlib import Path

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


def reset_theme(theme_name):
    temp_path = Path(f"~/.xfce-theme-studio/theme/{theme_name}.temp").expanduser()

    if temp_path.exists():
        shutil.rmtree(temp_path)






















    
