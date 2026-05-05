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
    Copie l'icône uploadée dans le thème temporaire au bon sous-dossier
    en gardant le nom de l'icône originale.

    theme_name : nom du thème actif
    category : onglet (Apps, Actions...)
    chemin_selectionne : chemin complet du fichier choisi
    icone_originale_nom : nom du fichier de l'icône à remplacer (ex: 'ark.png')
    """
    if not chemin_selectionne or not Path(chemin_selectionne).exists():
        return None

    temp_dir = get_temp_theme_dir(theme_name)
    dest_dir = temp_dir / category.lower()  # sous-dossier de la catégorie
    dest_dir.mkdir(parents=True, exist_ok=True)

    nom_icone = Path(icone_originale_path).name  # ex: "ark.png"

    # chemin final dans le temp
    dest_path = dest_dir / nom_icone

    print(nom_icone)
    print(dest_path)

    try:
        shutil.copy(chemin_selectionne, dest_path)
        global modifications_en_cours
        modifications_en_cours = True
        return dest_path
    except Exception as e:
        # Show error dialog - parent will be handled by caller
        print(f"Error applying icon: {e}")
        return None

def refresh_icone_widget(widget, chemin_image, load_image_func):
    """
    Met à jour un widget GTK Image avec la nouvelle icône.
    widget : Gtk.Image
    chemin_image : chemin complet vers l'image temporaire
    load_image_func : fonction load_image(path, size=(.., ..))
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
    Met à jour une cellule d'icône avec la nouvelle image.
    cell_widget est un Gtk.EventBox contenant un Gtk.Frame qui contient un Gtk.Box avec un Gtk.Image
    """
    from pathlib import Path
    if not Path(chemin_image).exists():
        return

    # charge image 64x64
    img = load_image_func(str(chemin_image), (64, 64))
    if not img:
        return

    # Scale to 64x64
    img = img.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)

    # Naviguer dans la structure : EventBox -> Frame -> VBox -> Image
    frame = None
    if isinstance(cell_widget, Gtk.EventBox):
        # EventBox peut contenir un Frame
        for child in cell_widget.get_children():
            if isinstance(child, Gtk.Frame):
                frame = child
                break
    elif isinstance(cell_widget, Gtk.Frame):
        frame = cell_widget

    if frame is None:
        return

    # Trouver le VBox à l'intérieur du Frame
    vbox = None
    for child in frame.get_children():
        if isinstance(child, Gtk.Box):
            vbox = child
            break

    if vbox is None:
        return

    # Trouver le Gtk.Image dans le VBox
    img_widget = None
    for child in vbox.get_children():
        if isinstance(child, Gtk.Image):
            img_widget = child
            break

    # Si aucun Image existant, ne rien faire (structure invalide)
    if img_widget is None:
        return

    # appliquer l'image
    img_widget.set_from_pixbuf(img)

def has_unsaved_changes():
    print(modifications_en_cours)
    return modifications_en_cours

def changeFalse() :
    global modifications_en_cours
    modifications_en_cours = False

