import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

APP_NAME = "Xfce Theme Studio"
DEFAULT_REPO = "https://github.com/SamouraiT3/Xfce-Theme-Studio"
DEFAULT_INSTALL = Path.home() / ".xfce-theme-studio"
GITHUB_API = "https://api.github.com/repos"

XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
MIME_PACKAGE_FILENAME = "xfce-theme-studio-xts.xml"
MIME_TYPE = "application/x-xts"
MIME_COMMENT = "Xfce Theme Studio project file"
MIME_GLOB = "*.xts"
MIME_ICON_NAME = "application-x-xts"
MIME_ICON_ASSET = Path(__file__).resolve().parents[1] / "assets" / "mime_icon.png"
DESKTOP_FILE_NAME = "xfce-theme-studio.desktop"

PYTHON_BIN = shutil.which("python3.12") or shutil.which("python3") or "python3"
PYTHON_DEPS = ["Pillow", "cairosvg"]


def normalize_version(v):
    if not v:
        return (0,)
    v = v.strip()
    match = re.match(r"^[vV]?(\d+(?:\.\d+)*)", v)
    if match:
        return tuple(int(x) for x in match.group(1).split("."))
    return (0,)


def compare_versions(a, b):
    a, b = normalize_version(a), normalize_version(b)
    return (a > b) - (a < b)


def read_installed_version(path: Path):
    version_file = path / ".version"
    return version_file.read_text().strip() if version_file.exists() else None


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
    req = urllib.request.Request(url, headers={"User-Agent": "xfce-theme-studio-update"})

    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.load(response)

    return {
        "tag": data.get("tag_name", "0.0.0"),
        "zip": data.get("zipball_url")
    }


def download(url, dst):
    with urllib.request.urlopen(url, timeout=20) as response:
        with open(dst, "wb") as out_file:
            shutil.copyfileobj(response, out_file)


def extract(zip_path, out_dir):
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(out_dir)


def clean_pycache(path):
    for root, dirs, files in os.walk(path):
        for filename in files:
            if filename.endswith(".pyc"):
                try:
                    os.remove(Path(root) / filename)
                except OSError:
                    pass
        for dirname in dirs:
            if dirname == "__pycache__":
                try:
                    shutil.rmtree(Path(root) / dirname)
                except OSError:
                    pass


def find_entry(folder):
    for file_path in folder.rglob("*.py"):
        if "venv" in file_path.parts:
            continue
        if file_path.name in ["main.py", "app.py", "run.py"]:
            return file_path

    for file_path in folder.rglob("*.py"):
        text = file_path.read_text(errors="ignore")
        if "__main__" in text:
            return file_path

    return next(folder.rglob("*.py"))


def get_current_version():
    return read_installed_version(DEFAULT_INSTALL)


def get_update_target():
    return DEFAULT_INSTALL


def is_update_available(local_version, remote_version):
    if local_version is None:
        return True
    return compare_versions(local_version, remote_version) < 0


def create_venv(path):
    if path.exists():
        shutil.rmtree(path)

    subprocess.run([PYTHON_BIN, "-m", "venv", "--system-site-packages", str(path)], check=True)


def install_python_deps(venv_path):
    pip = venv_path / "bin/pip"
    subprocess.run([str(pip), "install", "--upgrade", "pip"], check=False)
    subprocess.run([str(pip), "install"] + PYTHON_DEPS, check=True)


def create_launcher(install_dir, entry_file):
    launcher = install_dir / "xfce-theme-studio"
    python_bin = install_dir / "venv/bin/python"
    launcher.write_text(f"""#!/bin/bash
cd \"{install_dir}\"
\"{python_bin}\" \"{entry_file}\" "$@"
""")
    launcher.chmod(0o755)


def create_desktop_entry(install_dir):
    desktop_dir = Path.home() / ".local/share/applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = desktop_dir / DESKTOP_FILE_NAME
    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Xfce Theme Studio
Comment=Theme manager for XFCE
Exec={install_dir / 'xfce-theme-studio'} %f
Path={install_dir}
Icon=xfce-theme-studio
Terminal=false
Categories=Utility;System;Settings;
MimeType={MIME_TYPE};
"""
    desktop_file.write_text(desktop_content, encoding="utf-8")
    desktop_file.chmod(0o644)


def register_xts_mime_type(install_dir=None):
    """Register the .xts MIME type and set Xfce Theme Studio as the default application."""
    if install_dir is None:
        install_dir = DEFAULT_INSTALL

    mime_packages_dir = XDG_DATA_HOME / "mime" / "packages"
    mime_packages_dir.mkdir(parents=True, exist_ok=True)

    mime_package_file = mime_packages_dir / MIME_PACKAGE_FILENAME
    mime_package_file.write_text(
        f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<mime-info xmlns=\"http://www.freedesktop.org/standards/shared-mime-info\">
  <mime-type type=\"{MIME_TYPE}\">
    <comment>{MIME_COMMENT}</comment>
    <glob pattern=\"{MIME_GLOB}\"/>
  </mime-type>
</mime-info>
""",
        encoding="utf-8"
    )

    icon_dirs = [
        XDG_DATA_HOME / "icons" / "hicolor" / "48x48" / "mimetypes",
        XDG_DATA_HOME / "icons" / "hicolor" / "64x64" / "mimetypes",
        XDG_DATA_HOME / "icons" / "hicolor" / "scalable" / "mimetypes",
    ]

    if MIME_ICON_ASSET.exists():
        for icon_dir in icon_dirs:
            icon_dir.mkdir(parents=True, exist_ok=True)
            icon_target = icon_dir / f"{MIME_ICON_NAME}.png"
            shutil.copyfile(MIME_ICON_ASSET, icon_target)

    mime_db_dir = XDG_DATA_HOME / "mime"
    mime_db_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["update-mime-database", str(mime_db_dir)], check=False, capture_output=True)
    subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(XDG_DATA_HOME / "icons" / "hicolor")], check=False, capture_output=True)

    create_desktop_entry(install_dir)
    desktop_file = Path.home() / ".local/share/applications" / DESKTOP_FILE_NAME
    if desktop_file.exists():
        subprocess.run(["xdg-mime", "default", DESKTOP_FILE_NAME, MIME_TYPE], check=False, capture_output=True)

    return mime_package_file.exists()


def perform_update(release, install_dir=None):
    install_dir = Path(install_dir or get_update_target())
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        archive_path = temp_path / "release.zip"
        extract_path = temp_path / "release"

        download(release["zip"], archive_path)
        extract(archive_path, extract_path)
        source_root = next(extract_path.iterdir())

        if install_dir.exists():
            shutil.rmtree(install_dir)

        install_dir.mkdir(parents=True, exist_ok=True)
        app_dir = install_dir / "app"
        shutil.copytree(source_root, app_dir, dirs_exist_ok=True)

        clean_pycache(install_dir)
        (install_dir / ".version").write_text(release["tag"], encoding="utf-8")

        venv_path = install_dir / "venv"
        create_venv(venv_path)
        install_python_deps(venv_path)

        entry_file = find_entry(app_dir)
        create_launcher(install_dir, entry_file)
        create_desktop_entry(install_dir)
        register_xts_mime_type(install_dir)

    return install_dir


def is_installation_complete(install_dir=None):
    install_dir = Path(install_dir or DEFAULT_INSTALL)
    launcher = install_dir / "xfce-theme-studio"
    desktop_file = Path.home() / ".local/share/applications" / DESKTOP_FILE_NAME
    mime_package_file = XDG_DATA_HOME / "mime" / "packages" / MIME_PACKAGE_FILENAME
    icon_file = XDG_DATA_HOME / "icons" / "hicolor" / "48x48" / "mimetypes" / f"{MIME_ICON_NAME}.png"
    return (
        install_dir.exists()
        and (install_dir / "app").exists()
        and (install_dir / "venv").exists()
        and launcher.exists()
        and launcher.is_file()
        and os.access(str(launcher), os.X_OK)
        and desktop_file.exists()
        and mime_package_file.exists()
        and icon_file.exists()
    )


def ensure_installation(install_dir=None):
    install_dir = Path(install_dir or DEFAULT_INSTALL)
    if is_installation_complete(install_dir):
        return True
    try:
        latest = fetch_latest_release(DEFAULT_REPO)
        perform_update(latest, install_dir=install_dir)
    except Exception:
        return False
    return is_installation_complete(install_dir)
