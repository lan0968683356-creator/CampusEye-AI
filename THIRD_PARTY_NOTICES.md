# Third-party notices — CampusEye AI v1.1.0

This file documents project dependencies and known license-review items; it is **not** a substitute for legal review or the full license texts required by each component.

- **Ultralytics YOLOv8 family / pretrained model weights:** Ultralytics states that its trained models are licensed under **AGPL-3.0** by default, with a separate enterprise-license option. See https://www.ultralytics.com/license and https://github.com/ultralytics/ultralytics . A copy of the ONNX model was obtained through https://huggingface.co/Shad0ws/yolov8onnx . That third-party hosting page currently labels its repository MIT; provenance and redistribution rights for the underlying Ultralytics model must be independently established before public binary redistribution.
- **Flask:** Python web framework; see https://github.com/pallets/flask and the installed package's license.
- **OpenCV / opencv-python:** Computer vision runtime; see https://github.com/opencv/opencv and https://github.com/opencv/opencv-python for license files and bundled components.
- **NumPy:** Python array processing; see https://github.com/numpy/numpy and installed distribution for licenses of bundled libraries.
- **Werkzeug, Jinja2, Click, ItsDangerous, MarkupSafe** and any transitively installed packages: include appropriate notices as required by their actual versions/licenses.
- **Chart.js 4.4.7:** loaded from https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js ; see https://github.com/chartjs/Chart.js for license.
- **Google Fonts (DM Sans, Noto Sans TC):** loaded remotely. Check respective font notices if bundling their assets in the future; do not upload or redistribute font files here without confirming rights.
- **PyInstaller / Inno Setup:** Build tooling and resulting distribution may include bootloader/runtime or installer licensing requirements. Review the respective projects' licensing documentation and include required notices with the released installer.

## Before publishing the Windows installer

1. Verify that the model file is a redistributable derivative of a legitimately licensed model and include required AGPL text/source/attribution obligations.
2. Generate a list of **actual versions and licenses from the final bundled Windows installation**, including transitive binaries and any native libraries. This source-only ZIP does not prove which DLLs or packages are in the release EXE.
3. Make corresponding source and build/install scripts accessible for the exact released version, not just a generic newer/older commit.
4. Rebuild and review installer license screen and payload; compare its SHA-256 to uploaded GitHub Release asset.
5. Confirm no private user recordings, Wi-Fi credentials, API tokens, database files, or personal data are bundled.
