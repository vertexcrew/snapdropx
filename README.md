# SnapDropX 💧

**Drop a file. Share a link. Done.**

SnapDropX is a tiny, secure file-drop server with a modern web UI.
Upload files from one device, open the link on any other device —
no installs, no accounts, no setup.

**Live demo:** https://snapdropx.vercel.app 🔐 (login protected — ask the owner for access)

![SnapDropX Web UI](https://raw.githubusercontent.com/vertexcrew/snapdropx/main/assets/ui.png)

## What it does

- 📤 Drag & drop uploads with a live progress bar
- 📁 Folders, rename, delete (with confirm) — all from the browser
- 👁️ Preview images & text files without downloading
- 📦 Download any folder as a ZIP
- 🔁 Never overwrites silently — `report.pdf` becomes `report (1).pdf`
- 🔐 Every file route is login-protected; only `/health` is public
- 🔍 Search, live stats, 100 MB per-file cap (configurable)

## Run it locally

```bash
git clone https://github.com/vertexcrew/snapdropx.git
cd snapdropx
pip install -e .
snapdropx                 # opens on http://localhost:8000
```

With login and a folder of your choice:

```bash
snapdropx serve /path/to/files --port 8080 --auth username:password
```

## Deploy it

- **Vercel:** import this repo — it deploys on every push to `main`. Set `SNAPDROPX_AUTH` in environment variables first. Note: files on Vercel are temporary (demo use); for permanent storage use Render/Docker below.
- **Render / Docker:** `render.yaml` and `Dockerfile` are included. Always set `SNAPDROPX_AUTH` before going public — a public URL without login is never OK.

## Config

| Variable | Default | Purpose |
| --- | --- | --- |
| `SNAPDROPX_DIR` | `.` | Folder to serve |
| `SNAPDROPX_AUTH` | _(empty)_ | `username:password` — gates every file route |
| `SNAPDROPX_PORT` | `8000` | Port (Docker/Render) |
| `SNAPDROPX_MAX_UPLOAD_MB` | `100` | Per-file upload cap |

Tests: `pytest tests/ -v`

Made with ❤️ by Rayan · MIT License
