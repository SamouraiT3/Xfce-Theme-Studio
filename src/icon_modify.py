import os
import shutil
from pathlib import Path
from gi.repository import Gtk, GdkPixbuf

modifications_en_cours = False


def get_temp_theme_dir(theme_name):
    base = Path.home() / ".xfce-theme-studio" / "theme"
    return base / f"{theme_name}.temp"


def apply_new_icon(theme_name, category, chemin_selectionne, icone_originale_path):
    """
    Copy the uploaded icon into the theme temporary folder in the correct subfolder
    while keeping the original icon filename.

    theme_name : active theme name
    category : tab (Apps, Actions...)
    chemin_selectionne : full path of the chosen file
    icone_originale_nom : name of the icon file to replace (e.g. 'ark.png')
    """
    if not chemin_selectionne or not Path(chemin_selectionne).exists():
        return None

    temp_dir = get_temp_theme_dir(theme_name)
    dest_dir = temp_dir / category.lower()  # category subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)

    nom_icone = Path(icone_originale_path).name  # ex: "ark.png"

    dest_path = dest_dir / nom_icone

    try:
        shutil.copy(chemin_selectionne, dest_path)
        global modifications_en_cours
        modifications_en_cours = True
        return dest_path
    except Exception as e:
        print(f"Error applying icon: {e}")
        return None


def refresh_icone_widget(widget, chemin_image, load_image_func):
    """
    Update a Gtk.Image widget with the new icon.
    widget : Gtk.Image
    chemin_image : full path to the temporary image
    load_image_func : function load_image(path, size=(.., ..))
    """
    if not Path(chemin_image).exists():
        return

    img = load_image_func(str(chemin_image), (128, 128))
    if img:
        # Scale to 128x128
        img = img.scale_simple(128, 128, GdkPixbuf.InterpType.BILINEAR)
        widget.set_from_pixbuf(img)
    else:
        widget.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)


def refresh_icon_cell(cell_widget, chemin_image, load_image_func):
    """
    Update an icon cell with the new image.
    cell_widget is a Gtk.EventBox containing a Gtk.Frame which contains a Gtk.Box with a Gtk.Image
    """
    from pathlib import Path
    if not Path(chemin_image).exists():
        return

    # load image 64x64
    img = load_image_func(str(chemin_image), (64, 64))
    if not img:
        return

    # Scale to 64x64
    img = img.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)

    # Navigate structure: EventBox -> Frame -> VBox -> Image
    frame = None
    if isinstance(cell_widget, Gtk.EventBox):
        # EventBox may contain a Frame
        for child in cell_widget.get_children():
            if isinstance(child, Gtk.Frame):
                frame = child
                break
    elif isinstance(cell_widget, Gtk.Frame):
        frame = cell_widget

    if frame is None:
        return

    # Find the VBox inside the Frame
    vbox = None
    for child in frame.get_children():
        if isinstance(child, Gtk.Box):
            vbox = child
            break

    if vbox is None:
        return

    # Find the Gtk.Image in the VBox
    img_widget = None
    for child in vbox.get_children():
        if isinstance(child, Gtk.Image):
            img_widget = child
            break

    # If no existing Image, do nothing (invalid structure)
    if img_widget is None:
        return

    # apply the image
    img_widget.set_from_pixbuf(img)


def has_unsaved_changes():
    return modifications_en_cours


def changeFalse():
    global modifications_en_cours
    modifications_en_cours = False

