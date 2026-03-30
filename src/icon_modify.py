import os
import shutil
from pathlib import Path
from tkinter import messagebox
import tkinter as tk

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
        messagebox.showerror("Erreur", f"Impossible de changer l'icône : {e}")
        return None

def refresh_icone_widget(widget, chemin_image, load_image_func):
    """
    Met à jour un widget Tkinter avec la nouvelle icône.
    widget : label ou autre widget
    chemin_image : chemin complet vers l'image temporaire
    load_image_func : fonction load_image(path, size=(.., ..))
    """
    if not Path(chemin_image).exists():
        return

    img = load_image_func(str(chemin_image), (128,128))
    if img:
        # garder une référence stable
        if not hasattr(widget, "_image_refs"):
            widget._image_refs = {}
        widget._image_refs[str(chemin_image)] = img

        widget.config(image=img, text="")
        widget.image = img  # obligatoire pour Tkinter
    else:
        widget.config(image="", text=Path(chemin_image).name)

def refresh_icon_cell(cell_widget, chemin_image, load_image_func):
    """
    Met à jour une cellule d'icône (Frame contenant un Label) avec la nouvelle image.
    """
    from pathlib import Path
    if not Path(chemin_image).exists():
        return

    # charge image 64x64
    img = load_image_func(str(chemin_image), (64,64))
    if not img:
        return

    # trouver le Label enfant
    lbl = None
    for child in cell_widget.winfo_children():
        if isinstance(child, tk.Label):
            lbl = child
            break

    # si aucun Label existant, en créer un
    if lbl is None:
        lbl = tk.Label(cell_widget)
        lbl.pack(expand=True, fill="both")

    # stocker la référence
    if not hasattr(lbl, "_image_refs"):
        lbl._image_refs = {}
    lbl._image_refs[str(chemin_image)] = img

    # appliquer l'image
    lbl.config(image=img, text="")
    lbl.image = img  # 🔥 obligatoire

def has_unsaved_changes():
    print(modifications_en_cours)
    return modifications_en_cours

def changeFalse() :
    global modifications_en_cours
    modifications_en_cours = False

