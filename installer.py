import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

sys.dont_write_bytecode = True

# =========================================================
# CONFIG
# =========================================================

APP_NAME = "Xfce Theme Studio"
LAUNCHER_NAME = "xfce-theme-studio"

DEFAULT_REPO = "https://github.com/SamouraiT3/Xfce-Theme-Studio"
DEFAULT_INSTALL = Path.home() / ".xfce-theme-studio"

GITHUB_API = "https://api.github.com/repos"

PYTHON_BIN = shutil.which("python3.12") or shutil.which("python3") or "python3"

PYTHON_DEPS = ["Pillow", "cairosvg"]

# =========================================================
# LOG
# =========================================================

def log(widget, msg):
    widget.config(state="normal")
    widget.insert("end", msg + "\n")
    widget.see("end")
    widget.config(state="disabled")
    widget.update()

# =========================================================
# VERSION SYSTEM
# =========================================================

def normalize_version(v):
    if not v:
        return (0,)
    v = v.strip().lstrip("vV")
    return tuple(int(x) for x in re.findall(r"\d+", v))


def compare_versions(a, b):
    a, b = normalize_version(a), normalize_version(b)
    return (a > b) - (a < b)


def read_installed_version(path: Path):
    f = path / ".version"
    return f.read_text().strip() if f.exists() else None

# =========================================================
# SYSTEM DEPENDENCIES (XFCE SAFE)
# =========================================================

def detect_pm():
    for pm in ["apt", "dnf", "pacman", "zypper"]:
        if shutil.which(pm):
            return pm
    return None


def install_system_deps(logbox):
    pm = detect_pm()

    if not pm:
        log(logbox, "No package manager found, skipping system deps")
        return

    deps = {
        "apt": ["python3-gi", "gir1.2-gtk-3.0", "python3-cairo"],
        "dnf": ["python3-gobject", "gtk3", "python3-cairo"],
        "pacman": ["python-gobject", "gtk3", "python-cairo"],
        "zypper": ["python3-gobject", "gtk3", "python3-cairo"]
    }

    pkgs = deps.get(pm, [])

    log(logbox, f"Installing system deps ({pm})...")

    cmd = {
        "apt": ["pkexec", "apt", "install", "-y"],
        "dnf": ["pkexec", "dnf", "install", "-y"],
        "pacman": ["pkexec", "pacman", "-S", "--noconfirm"],
        "zypper": ["pkexec", "zypper", "--non-interactive", "install"]
    }[pm] + pkgs

    subprocess.run(cmd, check=False)

# =========================================================
# GITHUB RELEASE
# =========================================================

def parse_repo(url):
    url = url.replace(".git", "")
    url = url.replace("https://github.com/", "")
    url = url.replace("http://github.com/", "")
    url = url.replace("github.com/", "")
    owner, repo = url.strip("/").split("/")[:2]
    return owner, repo


def fetch_latest_release(repo_url):
    owner, repo = parse_repo(repo_url)

    url = f"{GITHUB_API}/{owner}/{repo}/releases/latest"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "xfce-installer"}
    )

    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)

    return {
        "tag": data.get("tag_name", "0.0.0"),
        "zip": data["zipball_url"]
    }

# =========================================================
# FILE OPS
# =========================================================

def download(url, dst):
    with urllib.request.urlopen(url) as r:
        with open(dst, "wb") as f:
            shutil.copyfileobj(r, f)


def extract(zip_path, out):
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(out)


def clean_pycache(path):
    for r, d, f in os.walk(path):
        for file in f:
            if file.endswith(".pyc"):
                try:
                    os.remove(Path(r) / file)
                except:
                    pass
        for dd in d:
            if dd == "__pycache__":
                try:
                    shutil.rmtree(Path(r) / dd)
                except:
                    pass

# =========================================================
# FIND ENTRY POINT
# =========================================================

def find_entry(folder):
    for f in folder.rglob("*.py"):
        if "venv" in f.parts:
            continue
        if f.name in ["main.py", "app.py", "run.py"]:
            return f

    for f in folder.rglob("*.py"):
        txt = f.read_text(errors="ignore")
        if "__main__" in txt:
            return f

    return next(folder.rglob("*.py"))

# =========================================================
# VENV
# =========================================================

def create_venv(path, logbox):
    if path.exists():
        shutil.rmtree(path)

    log(logbox, "Creating venv...")

    subprocess.run([
        PYTHON_BIN,
        "-m",
        "venv",
        "--system-site-packages",
        str(path)
    ], check=True)

# =========================================================
# PYTHON DEPS
# =========================================================

def install_python_deps(venv, logbox):
    pip = venv / "bin/pip"

    log(logbox, "Installing Python deps...")

    subprocess.run([str(pip), "install", "--upgrade", "pip"], check=False)

    r = subprocess.run(
        [str(pip), "install"] + PYTHON_DEPS,
        capture_output=True,
        text=True
    )

    if r.returncode != 0:
        raise RuntimeError(r.stderr)

# =========================================================
# LAUNCHER
# =========================================================

def create_launcher(install_dir, entry):
    launcher = install_dir / LAUNCHER_NAME
    py = install_dir / "venv/bin/python"

    launcher.write_text(f"""#!/bin/bash
cd "{install_dir}"
"{py}" "{entry}" "$@"
""")

    launcher.chmod(0o755)

# =========================================================
# INSTALL ICON
# =========================================================

def install_system_icon(install_dir: Path, logbox):
    icon_png = install_dir / "app/assets/icon.png"
    icon_svg = install_dir / "app/assets/icon.svg"

    if not icon_png.exists() and not icon_svg.exists():
        return False

    target_base = Path("/usr/share/icons/hicolor")

    sizes = {
        "png": "48x48/apps/xfce-theme-studio.png",
        "svg": "scalable/apps/xfce-theme-studio.svg"
    }

    try:
        if icon_png.exists():
            target = target_base / sizes["png"]
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["pkexec", "cp", str(icon_png), str(target)], check=True)

        if icon_svg.exists():
            target = target_base / sizes["svg"]
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["pkexec", "cp", str(icon_svg), str(target)], check=True)

        subprocess.run(
            ["pkexec", "gtk-update-icon-cache", "hicolor"],
            check=False
        )

        log(logbox, "System icon installed in hicolor theme")

        return True

    except Exception as e:
        log(logbox, f"Icon install failed: {e}")
        return False

# =========================================================
# DESKTOP GENERATION
# =========================================================

def register_xts_mime_type_installer(install_dir: Path, logbox):
    """Register the .xts MIME type and set Xfce Theme Studio as the default application."""
    xdg_data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    mime_packages_dir = xdg_data_home / "mime" / "packages"
    mime_packages_dir.mkdir(parents=True, exist_ok=True)

    mime_package_file = mime_packages_dir / "xfce-theme-studio-xts.xml"
    mime_package_file.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-xts">
    <comment>Xfce Theme Studio project file</comment>
    <glob pattern="*.xts"/>
  </mime-type>
</mime-info>
""",
        encoding="utf-8"
    )

    log(logbox, "Registering .xts MIME type...")

    icon_dirs = [
        xdg_data_home / "icons" / "hicolor" / "48x48" / "mimetypes",
        xdg_data_home / "icons" / "hicolor" / "64x64" / "mimetypes",
        xdg_data_home / "icons" / "hicolor" / "scalable" / "mimetypes",
    ]

    mime_icon_asset = Path(__file__).resolve().parent / "assets" / "mime_icon.png"
    if mime_icon_asset.exists():
        for icon_dir in icon_dirs:
            icon_dir.mkdir(parents=True, exist_ok=True)
            icon_target = icon_dir / "application-x-xts.png"
            try:
                shutil.copyfile(mime_icon_asset, icon_target)
            except Exception as e:
                log(logbox, f"Warning: Failed to copy MIME icon to {icon_target}: {e}")

    mime_db_dir = xdg_data_home / "mime"
    mime_db_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["update-mime-database", str(mime_db_dir)], check=False, capture_output=True)
    subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(xdg_data_home / "icons" / "hicolor")], check=False, capture_output=True)

    subprocess.run(["xdg-mime", "default", "xfce-theme-studio.desktop", "application/x-xts"], check=False, capture_output=True)
    log(logbox, "MIME type registration complete\n")


def create_desktop_entry(install_dir: Path, logbox):
    desktop_dir = Path.home() / ".local/share/applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)

    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Xfce Theme Studio
Comment=Theme manager for XFCE
Exec={install_dir / "xfce-theme-studio"} %f
Path={install_dir}
Icon=xfce-theme-studio
Terminal=false
Categories=Utility;System;Settings;
MimeType=application/x-xts;
"""

    desktop_file = desktop_dir / "xfce-theme-studio.desktop"
    desktop_file.write_text(desktop_content, encoding="utf-8")
    desktop_file.chmod(0o644)

    logbox.insert("end", "Desktop entry created\n")

    return desktop_file


# =========================================================
# INSTALL CORE
# =========================================================

def install_app(install_dir, release, logbox):

    with tempfile.TemporaryDirectory() as t:
        t = Path(t)

        zipf = t / "r.zip"
        out = t / "out"

        log(logbox, "Downloading release...")
        download(release["zip"], zipf)

        log(logbox, "Extracting...")
        extract(zipf, out)

        root = next(out.iterdir())

        if install_dir.exists():
            shutil.rmtree(install_dir)

        install_dir.mkdir()

        app = install_dir / "app"
        shutil.copytree(root, app, dirs_exist_ok=True)

        clean_pycache(install_dir)

        log(logbox, "Finding entry...")
        entry = find_entry(app)

        log(logbox, f"Entry: {entry}")

        (install_dir / ".version").write_text(release["tag"])

        install_system_deps(logbox)

        venv = install_dir / "venv"
        create_venv(venv, logbox)

        install_python_deps(venv, logbox)

        create_launcher(install_dir, entry)

        install_system_icon(install_dir, logbox)

        create_desktop_entry(install_dir, logbox)

        register_xts_mime_type_installer(install_dir, logbox)

        log(logbox, "INSTALL COMPLETE")

# =========================================================
# GUI
# =========================================================

class GUI:
    def __init__(self, root):
        self.root = root
        root.title("Xfce Theme Studio Installer")
        root.geometry("500x400")
        root.minsize(500, 400)

        self.repo = tk.Entry(root)
        self.repo.insert(0, DEFAULT_REPO)
        self.repo.pack(fill="x")
        self.repo.config(state="disabled")

        self.install = tk.Entry(root)
        self.install.insert(0, str(DEFAULT_INSTALL))
        self.install.pack(fill="x")
        self.install.config(state="disabled")

        self.logbox = scrolledtext.ScrolledText(root, width=80, height=15)
        self.logbox.pack(fill="both", expand=True)


        self.check_btn = tk.Button(root, text="Check update", command=self.check)
        self.check_btn.pack()

        self.install_btn = tk.Button(root, text="Install / Update", command=self.install_app)
        self.install_btn.pack()

        self.check()

    def set_status(self, msg):
        log(self.logbox, msg)

    def check(self):

        self.logbox.config(state="normal")
        self.logbox.delete("1.0", "end")
        self.logbox.config(state="disabled")
        
        try:
            rel = fetch_latest_release(self.repo.get())
            installed = read_installed_version(Path(self.install.get()))

            log(self.logbox, f"Latest: {rel['tag']}")

            if installed:
                log(self.logbox, f"Installed: {installed}")

                if compare_versions(installed, rel["tag"]) < 0:
                    log(self.logbox, "Update available")
                else:
                    log(self.logbox, "Up to date")
            else:
                log(self.logbox, "Not installed")

        except Exception as e:
            log(self.logbox, str(e))

    def install_app(self):
        self.install_btn.config(state="disabled")
        self.check_btn.config(state="disabled")
        try:
            rel = fetch_latest_release(self.repo.get())
            install_app(Path(self.install.get()), rel, self.logbox)
            messagebox.showinfo("OK", "Installation complete")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            log(self.logbox, str(e))
        finally:
            self.install_btn.config(state="normal")
            self.check_btn.config(state="normal")


# =========================================================
# MAIN
# =========================================================

def main():
    root = tk.Tk()
    GUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
