"""Command-line installer for Xfce Theme Studio."""

import argparse
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

APP_NAME = "Xfce Theme Studio"
LAUNCHER_NAME = "xfce-theme-studio"
DEFAULT_REPO = "https://github.com/SamouraiT3/Xfce-Theme-Studio"
DEFAULT_INSTALL = Path.home() / ".xfce-theme-studio"
GITHUB_API = "https://api.github.com/repos"
PYTHON_DEPS = ["Pillow", "cairosvg"]

SYSTEM_PACKAGES = {
    "apt-get": [
        "python3-gi", "gir1.2-gtk-3.0", "python3-cairo", "python3-venv",
        "python3-pip", "shared-mime-info", "xdg-utils",
    ],
    "dnf": [
        "python3-gobject", "gtk3", "python3-cairo", "python3-pip",
        "shared-mime-info", "xdg-utils",
    ],
    "pacman": [
        "python-gobject", "gtk3", "python-cairo", "python-pip",
        "shared-mime-info", "xdg-utils",
    ],
    "zypper": [
        "python3-gobject", "gtk3", "python3-cairo", "python3-pip",
        "shared-mime-info", "xdg-utils",
    ],
}


def log(message):
    print(f"[Xfce Theme Studio] {message}", flush=True)


def normalize_version(version):
    if not version:
        return (0,)
    match = re.match(r"^[vV]?(\d+(?:\.\d+)*)", version.strip())
    return tuple(int(part) for part in match.group(1).split(".")) if match else (0,)


def compare_versions(left, right):
    left_version = normalize_version(left)
    right_version = normalize_version(right)
    return (left_version > right_version) - (left_version < right_version)


def read_installed_version(path):
    try:
        return (Path(path) / ".version").read_text(encoding="utf-8").strip()
    except OSError:
        return None


def installation_is_complete(path):
    install_dir = Path(path)
    launcher = install_dir / LAUNCHER_NAME
    return (
        (install_dir / "app").is_dir()
        and (install_dir / "venv" / "bin" / "python").is_file()
        and launcher.is_file()
        and os.access(launcher, os.X_OK)
    )


def parse_repo(url):
    parts = url.removesuffix(".git").rstrip("/").split("/")
    try:
        github_index = parts.index("github.com")
        return parts[github_index + 1], parts[github_index + 2]
    except (ValueError, IndexError):
        raise ValueError(f"URL GitHub invalide : {url}") from None


def fetch_latest_release(repo_url):
    owner, repo = parse_repo(repo_url)
    request = urllib.request.Request(
        f"{GITHUB_API}/{owner}/{repo}/releases/latest",
        headers={"User-Agent": "xfce-theme-studio-installer"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    if not release.get("zipball_url"):
        raise RuntimeError("La dernière release ne contient pas d'archive ZIP.")
    return {"tag": release.get("tag_name", "0.0.0"), "zip": release["zipball_url"]}


def download(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": "xfce-theme-studio-installer"})
    with urllib.request.urlopen(request, timeout=60) as response, open(destination, "wb") as output:
        shutil.copyfileobj(response, output)


def extract(zip_path, destination):
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(destination)


def clean_pycache(path):
    for root, directories, files in os.walk(path):
        for filename in files:
            if filename.endswith(".pyc"):
                Path(root, filename).unlink(missing_ok=True)
        for directory in directories:
            if directory == "__pycache__":
                shutil.rmtree(Path(root, directory), ignore_errors=True)


def find_entry(folder):
    python_files = [file_path for file_path in folder.rglob("*.py") if "venv" not in file_path.parts]
    for file_path in python_files:
        if file_path.name in {"main.py", "app.py", "run.py"}:
            return file_path
    for file_path in python_files:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        if "__main__" in text:
            return file_path
    return python_files[0] if python_files else None


def detect_package_manager():
    for manager in SYSTEM_PACKAGES:
        if shutil.which(manager):
            return manager
    return None


def apt_package_installed(package):
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${Status}", package],
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() == "install ok installed"


def missing_system_packages(manager):
    packages = SYSTEM_PACKAGES[manager]
    if manager == "apt-get" and shutil.which("dpkg-query"):
        return [package for package in packages if not apt_package_installed(package)]
    return packages


def run_privileged(command):
    if shutil.which("pkexec"):
        return subprocess.run(["pkexec"] + command, check=False).returncode == 0
    if shutil.which("sudo"):
        return subprocess.run(["sudo"] + command, check=False).returncode == 0
    return False


def ensure_system_dependencies(skip=False):
    if skip:
        log("Vérification des paquets système ignorée (--no-system-deps).")
        return
    manager = detect_package_manager()
    if not manager:
        raise RuntimeError("Aucun gestionnaire de paquets supporté trouvé.")
    missing = missing_system_packages(manager)
    if not missing:
        log("Paquets système déjà présents.")
        return
    log(f"Paquets système manquants ({manager}) : {', '.join(missing)}")
    commands = {
        "apt-get": [["apt-get", "update"], ["apt-get", "install", "-y"] + missing],
        "dnf": [["dnf", "install", "-y"] + missing],
        "pacman": [["pacman", "-Sy", "--noconfirm"] + missing],
        "zypper": [["zypper", "--non-interactive", "install"] + missing],
    }[manager]
    for command in commands:
        log("Exécution : " + " ".join(command))
        if not run_privileged(command):
            raise RuntimeError("Impossible d'installer les paquets système avec pkexec ou sudo.")


def verify_python_modules(python_executable):
    checks = {"gi": "PyGObject (python3-gi)", "cairo": "PyCairo (python3-cairo)"}
    missing = []
    for module, label in checks.items():
        result = subprocess.run(
            [str(python_executable), "-c", f"import {module}"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            missing.append(label)
    if missing:
        raise RuntimeError("Modules Python système manquants : " + ", ".join(missing))


def create_venv(path, python_executable):
    log(f"Création du venv avec {python_executable}...")
    subprocess.run(
        [str(python_executable), "-m", "venv", "--system-site-packages", str(path)],
        check=True,
    )


def install_python_dependencies(venv):
    python = venv / "bin" / "python"
    pip_check = subprocess.run([str(python), "-m", "pip", "--version"], check=False)
    if pip_check.returncode:
        raise RuntimeError("pip est absent du venv. Installez python3-venv et python3-pip.")
    log("Installation des dépendances Python : Pillow, cairosvg...")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--disable-pip-version-check"] + PYTHON_DEPS,
        check=True,
    )
    verify_python_modules(python)


def create_launcher(install_dir, entry):
    launcher = install_dir / LAUNCHER_NAME
    relative_entry = entry.relative_to(install_dir)
    launcher.write_text(
        '#!/bin/sh\n'
        'DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\n'
        f'exec "$DIR/venv/bin/python" "$DIR/{relative_entry}" "$@"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o755)


def safe_run(command):
    if shutil.which(command[0]):
        subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def create_desktop_entry(install_dir):
    desktop_dir = Path.home() / ".local/share/applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = desktop_dir / "xfce-theme-studio.desktop"
    desktop_file.write_text(
        f"""[Desktop Entry]
Version=1.0
Type=Application
Name={APP_NAME}
Comment=Theme manager for XFCE
Exec={install_dir / LAUNCHER_NAME} %f
Path={install_dir}
Icon=xfce-theme-studio
Terminal=false
Categories=Utility;System;Settings;
MimeType=application/x-xts;
""",
        encoding="utf-8",
    )
    desktop_file.chmod(0o644)
    safe_run(["update-desktop-database", str(desktop_dir)])


def install_user_icon(install_dir):
    icon_source = install_dir / "app" / "assets" / "icon.png"
    if not icon_source.exists():
        return
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    icon_target = data_home / "icons" / "hicolor" / "48x48" / "apps" / "xfce-theme-studio.png"
    icon_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(icon_source, icon_target)


def register_mime_type(install_dir):
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    mime_dir = data_home / "mime"
    packages_dir = mime_dir / "packages"
    packages_dir.mkdir(parents=True, exist_ok=True)
    (packages_dir / "xfce-theme-studio-xts.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-xts">
    <comment>Xfce Theme Studio project file</comment>
    <glob pattern="*.xts"/>
  </mime-type>
</mime-info>
""",
        encoding="utf-8",
    )
    safe_run(["update-mime-database", str(mime_dir)])
    install_user_icon(install_dir)
    create_desktop_entry(install_dir)
    safe_run(["xdg-mime", "default", "xfce-theme-studio.desktop", "application/x-xts"])


def install(release, install_dir, skip_system_deps=False):
    install_dir = Path(install_dir).expanduser()
    python_executable = Path(shutil.which("python3") or sys.executable)
    ensure_system_dependencies(skip_system_deps)
    verify_python_modules(python_executable)

    with tempfile.TemporaryDirectory(prefix="xfce-theme-studio-") as temporary:
        temporary = Path(temporary)
        archive = temporary / "release.zip"
        extracted = temporary / "release"
        staged = temporary / "install"
        log("Téléchargement de la release...")
        download(release["zip"], archive)
        log("Extraction...")
        extract(archive, extracted)
        source = next(extracted.iterdir(), None)
        if source is None:
            raise RuntimeError("L'archive téléchargée est vide.")
        app = staged / "app"
        shutil.copytree(source, app)
        clean_pycache(staged)
        entry = find_entry(app)
        if entry is None:
            raise RuntimeError("Aucun point d'entrée Python trouvé dans la release.")
        (staged / ".version").write_text(release["tag"], encoding="utf-8")
        venv = staged / "venv"
        create_venv(venv, python_executable)
        install_python_dependencies(venv)
        create_launcher(staged, entry)

        backup = install_dir.with_name(install_dir.name + ".backup")
        if backup.exists():
            shutil.rmtree(backup)
        install_dir.parent.mkdir(parents=True, exist_ok=True)
        if install_dir.exists():
            install_dir.rename(backup)
        try:
            shutil.move(str(staged), str(install_dir))
            register_mime_type(install_dir)
        except Exception:
            if install_dir.exists():
                shutil.rmtree(install_dir, ignore_errors=True)
            if backup.exists():
                backup.rename(install_dir)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    log(f"Installation terminée : {install_dir}")


def main():
    parser = argparse.ArgumentParser(description=f"Installer {APP_NAME} sans interface graphique")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="URL du dépôt GitHub")
    parser.add_argument("--install-dir", type=Path, default=DEFAULT_INSTALL)
    parser.add_argument("--check", action="store_true", help="Afficher la version disponible sans installer")
    parser.add_argument("--yes", action="store_true", help="Ne pas demander de confirmation")
    parser.add_argument("--no-system-deps", action="store_true", help="Ne pas installer les paquets système")
    args = parser.parse_args()

    try:
        release = fetch_latest_release(args.repo)
        installed = read_installed_version(args.install_dir)
        log(f"Version disponible : {release['tag']}")
        log(f"Version installée : {installed or 'aucune'}")
        if args.check:
            return 0
        if installed and compare_versions(installed, release["tag"]) >= 0 and installation_is_complete(args.install_dir):
            log("La version installée est déjà à jour.")
            return 0
        if not args.yes and input("Continuer l'installation ? [o/N] ").strip().lower() not in {"o", "oui", "y", "yes"}:
            log("Installation annulée.")
            return 0
        install(release, args.install_dir, args.no_system_deps)
        return 0
    except (OSError, subprocess.CalledProcessError, RuntimeError, ValueError) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
