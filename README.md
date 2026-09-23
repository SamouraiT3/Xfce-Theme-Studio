<h1>
  Xfce Theme Studio
  <img src="assets/icon.png" width="48" style="vertical-align: middle;" />
</h1>


A simple graphical tool to create and customize icon themes for Xfce on Linux

> **Project temporarily on hold**
>
> Development of Xfce Theme Studio is currently halted. The project may be resumed later, but no new features or fixes are planned for the time being.

## Description

Xfce Theme Studio is a Python application using PyGObject that allows users to easily create and modify icon themes for the Xfce desktop environment. The intuitive interface facilitates icon management by categories (applications, places, devices, actions, status) and supports SVG and PNG formats.

## Main Features

- Creation of new icon themes
- Modification of existing icons
- Management of system and user themes
- Support for theme inheritance
- Simple and intuitive graphical interface
- Support for SVG and PNG formats

# Installation

1. Download `installer.py` from the Releases section.
2. Open a terminal in the download directory (`cd 'directory'`).
3. Check the latest version and the current installation:
  `python3 installer.py --check`
4. Install or update from the terminal:
  `python3 installer.py`

The installer has no Tkinter dependency. It checks for the required Mint/Debian
packages (`python3-gi`, GTK 3, Cairo, `python3-venv`, `python3-pip`, MIME and
XDG tools), asks for administrator permission only when packages are missing,
and installs Pillow and CairoSVG in a local virtual environment. Use
`python3 installer.py --yes` for a non-interactive install, or
`--no-system-deps` only when those system packages are already installed.

## Screenshots

![Icon Modification](assets/screenshot1.png) 
![Mimetype Modification](assets/screenshot2.png)
![Interface](assets/screenshot3.png)
![GTK Theme Modification](assets/screenshot4.png)


## Dependencies

- Python 3
- PyGObject
- Pillow (PIL)
- CairoSVG

## License

This project is licensed under the GNU General Public License v3.0.

## Author

 **Developed by Samourai-T3**

**Community contributions are welcome.**

You can help improve `theme_structure.py` by adding new customizable elements and parameters.

- Open a Pull Request
- Or send your `theme_structure.py` file by email to: samourai.t3@gmail.com

An example structure is available in:


`examples/theme_structure.py`


## Version


### Current version : 

**v4.0.0**
- xfwm4 theme support

### Next versions:

**v4.x.x**
- Bug fix
- GTK options update

Project on hold