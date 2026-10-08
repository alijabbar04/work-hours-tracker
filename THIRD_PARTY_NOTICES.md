# Third-party software

Work Hours Tracker's application code is MIT-licensed. Its dependencies retain their own licences and copyrights. The Windows executable includes Python, Tcl/Tk and supporting libraries; those are not relicensed by this project's MIT licence.

The direct libraries used are:

| Component | Purpose | Upstream |
| --- | --- | --- |
| Python / Tkinter / Tcl/Tk | Runtime and desktop interface | [Python](https://www.python.org/), [Tcl/Tk](https://www.tcl-lang.org/) |
| openpyxl | Excel workbook reading/writing | [openpyxl](https://openpyxl.readthedocs.io/) |
| keyring | Operating-system credential storage | [keyring](https://github.com/jaraco/keyring) |
| Requests | Optional desktop AI HTTP requests | [Requests](https://requests.readthedocs.io/) |
| ReportLab | PDF generation | [ReportLab](https://www.reportlab.com/) |
| Matplotlib | Dashboard charts | [Matplotlib](https://matplotlib.org/) |
| Pillow | Images and app-icon generation | [Pillow](https://python-pillow.org/) |
| PyInstaller | Executable packaging and bootloader | [PyInstaller](https://pyinstaller.org/) |

Transitive dependencies are installed from their published distributions. The release package's `licenses/` folder contains texts collected from the build environment's installed distribution licence files, Matplotlib fonts and the Python/Tcl/Tk runtime. Upstream author names in those licence texts identify those projects, not users of this app.

PyInstaller's bootloader distribution exception permits distributing bundled application executables under their application's terms. Its source/tooling retains its upstream licence. Consult the included upstream texts for the exact terms.
