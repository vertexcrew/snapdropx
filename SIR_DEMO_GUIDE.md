# SnapDropX v2 — How to Use + Demo Guide (for Sir)

## What is SnapDropX? (one line)
SnapDropX is a secure, zero-config file-sharing server: run one command, open a
link in any browser, and upload / download / manage files from any device —
no app install, no account needed on the viewer's side.

## The problem it solves
- Sending files by pen drive, email attachments, or chat apps is slow and has
  size limits.
- `python -m http.server` shares files but has no upload, no login, and no
  protection against path-traversal attacks.
- SnapDropX adds uploads, login protection, and safe path handling in one
  small FastAPI app.

## How to run it (local)
```bash
pip install -e .
snapdropx                    # serves the current folder on port 8000
snapdropx /path/to/files     # serve a specific folder
snapdropx --port 8080        # custom port
snapdropx --auth user:pass   # protect with username + password
snapdropx --ssl              # HTTPS with a self-signed certificate
```

## How a friend in another country views your files
1. Deploy SnapDropX on a public server (Render / Docker — see `render.yaml`
   and `Dockerfile` in this repo), OR expose your local server with a tunnel
   for a temporary demo link.
2. Upload your files through the web UI.
3. Send the public link to your friend.
4. Your friend opens the link in any browser, logs in with the username +
   password you share, and can browse, preview, and download files.
   They install nothing.
5. Rule: a public link MUST have auth enabled (`SNAPDROPX_AUTH=user:pass`).
   Without login, nobody can see even a single file name.

## Features (v2.0.0)
- Drag & drop uploads with a progress bar
- Browse folders, search files
- Preview images and text files without downloading
- Download a whole folder as a ZIP
- Create folder, rename, delete (with confirmation)
- Duplicate uploads never overwrite: `report.pdf` becomes `report (1).pdf`
- Per-file upload size limit (default 100 MB, via `SNAPDROPX_MAX_UPLOAD_MB`)
- HTTP Basic Auth on EVERY route (listing, download, preview, ZIP, API)
- Path-traversal protection (cannot escape the served folder)
- Optional self-signed HTTPS
- Health endpoint (`/health`) for hosting platforms
- Tests: 55 automated tests (security, auth, upload, download, zip, stats)

## Architecture (for the viva)
- **FastAPI + Uvicorn** — the web framework and server.
- **Typer CLI** — the `snapdropx` command.
- **Jinja2 templates + plain JS/CSS** — the web UI (no heavy frontend build).
- **Security module** — Basic Auth with constant-time comparison, path
  sanitisation, self-signed certificate generation.
- **Storage** — plain files on disk inside one sandboxed folder; no database
  needed, which keeps it fast and simple.

## API (for the demo)
| Method | Endpoint          | What it does              |
|--------|-------------------|---------------------------|
| GET    | `/`               | File listing (web UI)     |
| GET    | `/browse/{path}`  | Open a subfolder          |
| GET    | `/download/{path}`| Download a file           |
| GET    | `/preview/{path}` | Preview image/text inline |
| GET    | `/zip/{path}`     | Download a folder as ZIP  |
| POST   | `/upload`         | Upload files              |
| POST   | `/mkdir`          | Create a folder           |
| POST   | `/rename`         | Rename a file/folder      |
| DELETE | `/delete/{path}`  | Delete a file/empty dir   |
| GET    | `/api/files`      | JSON file listing         |
| GET    | `/api/stats`      | File/folder counts + size |
| GET    | `/health`         | Health check (public)     |

## 2-minute demo script (do this in front of Sir)
1. Start the server and open the link. Point out the login prompt — this is
   the auth protection.
2. Drag & drop a file, watch the progress bar, then show it in the list.
3. Upload the same file again — show it becomes `file (1).ext`, nothing is
   lost by overwriting.
4. Click Preview on a photo/text file — it opens without downloading.
5. Select a folder and download it as a ZIP.
6. Create a folder, rename a file, delete a file (confirm dialog shows).
7. Open the same link on your phone — same UI, no install.
8. Closing line: "Sir, local version same WiFi pe chalta hai; public deploy
   pe India se US tak koi bhi browser se login karke files dekh sakta hai —
   aur bina login ke ek file ka naam bhi nahi dikhta."

## Limitations (honest answers if Sir asks)
- One server = one shared folder; there are no per-user accounts or
  per-user folders yet.
- Basic Auth should run over HTTPS in production; on plain HTTP the
  password travels encoded, not encrypted.
- Very large files are limited by the upload cap and server disk space.
- The public demo tunnel link is temporary; the permanent setup is the
  Render/Docker deployment in this repo.

## Vercel note (if Sir asks why the first deploy failed)
The first Vercel deployment failed because the old repo had no Vercel
configuration at all — Vercel cannot run a plain long-running uvicorn
server. v2.0.0 adds `vercel.json` + `api/index.py` (FastAPI wrapped with
Mangum as a serverless function), so Vercel now deploys on every push to
`main`. One honest caveat for the demo: uploads on Vercel are temporary
and may disappear; the permanent setup is Render/Docker.
