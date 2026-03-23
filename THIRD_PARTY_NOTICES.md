# Third-Party Notices

This project uses third-party Python libraries and optional native tools as supporting dependencies. The project code in this repository is separate from those upstream works.

## Python dependencies used by this repository

The following license snapshot was checked on 2026-03-23 from the current PyPI project pages.

| Dependency | Role in this project | License snapshot |
|---|---|---|
| Pillow | Image loading and screenshot processing | `MIT-CMU` |
| PyAutoGUI | Cross-platform mouse and keyboard automation fallback | `BSD License (BSD)` |
| PyGetWindow | Window enumeration and activation on Windows | `BSD License (BSD)` |
| pytesseract | Python wrapper for OCR | `Apache License 2.0` |
| opencv-python | Template matching and image processing | PyPI metadata says `Apache 2.0`; project page also notes the wrapper package scripts are under `MIT` while OpenCV itself is under `Apache 2.0` |
| numpy | Numeric arrays used by image-processing helpers | `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` |

## Native tools expected by some workflows

These tools are not bundled by this repository, but the skill may call them when present:

- `cliclick`
- `tesseract`
- `xdotool`
- `wmctrl`

Before redistributing those binaries yourself, verify their own licenses and redistribution terms separately.

## Repository release note

This file is an operational license inventory, not legal advice. Before public release, add a root `LICENSE` file for this repository and confirm that any bundled assets, scripts, or binaries are covered by terms you are allowed to redistribute.
