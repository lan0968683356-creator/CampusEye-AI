# GitHub release preflight (not yet approved)

- [ ] GitHub repository has **full AGPL-3.0 `LICENSE`** at the root.
- [ ] `app.py`, `launcher.py`, `static/`, `templates/`, build/download scripts and requirements match the installer being released.
- [ ] Source commit/tag used for the Release is verified (attach the installer to a tag matching source).
- [ ] Model provenance and permission to redistribute `yolov8n.onnx` are confirmed; include required source/weight details and attribution.
- [ ] Third-party licenses/notices for the **actual frozen installer dependencies** are checked and provided as required.
- [ ] Fresh Windows installer is rebuilt from published source with an updated license screen; original installer should be replaced, not silently reused.
- [ ] Installer internals were reviewed and verified free of user videos, databases, secrets and credentials.
- [ ] Software works on a second Windows machine; offline limitations are disclosed.
- [ ] Final SHA-256 for newly built installer is computed and published.
- [ ] After all above, publish release. Until then keep it as **Draft**.
