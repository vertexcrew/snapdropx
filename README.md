🚀 SnapDropX v2.0.0

Secure · Zero-Config · Local File Drop Server

SnapDropX is a modern, secure alternative to python -m http.server with a
beautiful web UI, drag-and-drop uploads, authentication, and HTTPS support.
Perfect for quickly sharing files between machines or within a local network.

✨ Features

🔐 Secure by Default (Optional HTTP Basic Auth)

📤 Drag & Drop File Uploads with a live progress bar

📁 Create folders, rename, and delete from the UI (delete asks first)

👁️ In-browser preview for images and text files (in a modal)

📦 Download any folder as a ZIP

📊 Live stats line: file/folder counts and total size

🔁 Smart uploads: never silently overwrites — `report.pdf` becomes
   `report (1).pdf`, `report (2).pdf`, … and the final name is reported

📏 Per-file upload size cap (default 100 MB, configurable)

⚡ Starts in under 1 second

🎨 Modern, responsive UI (Desktop + Mobile)

🔍 Search & filter files

🛡️ Path traversal protection

🔒 HTTPS support with self-signed SSL

---

## 🖥️ Preview

![SnapDropX Web UI](https://raw.githubusercontent.com/vertexcrew/snapdropx/main/assets/ui.png)


> Clean, modern, mobile-friendly interface with drag-and-drop uploads.

## 🚀 Installation
git clone https://github.com/vertexcrew/snapdropx.git
cd snapdropx
pip install -e .

## ▶️ Usage
Start server (current directory)
snapdropx

## Open in browser:
http://localhost:8000

Serve specific directory
snapdropx serve /path/to/files

Custom port
snapdropx serve --port 8080

Enable authentication
snapdropx serve --auth username:password

## Browser will ask for username & password

Enable HTTPS (self-signed SSL)
snapdropx serve --ssl

Full secure configuration
snapdropx serve /data --port 8443 --auth admin:secret --ssl

Access from other devices (LAN)
snapdropx serve --host 0.0.0.0 --port 8000 --auth user:pass

## Open on phone / other PC:
http://YOUR_LOCAL_IP:8000

## 🌐 Deploying (Render / Docker)

One-click Render deploy: push this repo to Render with the included
`render.yaml` (free web service, `pip install .` build, uvicorn start).
It runs:

uvicorn snapdropx.main:app --host 0.0.0.0 --port $PORT

Docker:

docker build -t snapdropx .
docker run -p 8000:8000 -e SNAPDROPX_AUTH=user:pass snapdropx

> ⚠️ NEVER deploy publicly without auth. Set `SNAPDROPX_AUTH` to a
> `username:password` value before going live — see "Authentication"
> below. Local LAN-only use may run without auth; public use must not.

## ▲ Deploying (Vercel)

Vercel runs Python as serverless functions, so this repo ships a
`vercel.json` + `api/index.py` entrypoint (FastAPI wrapped with Mangum).
Import the repo in Vercel and it deploys on every push to `main`.

> ⚠️ Vercel uploads are **ephemeral**: files live only while the function
> instance is warm and may disappear. Use Vercel for a browse / preview /
> download demo; use the Render/Docker deployment above for a permanent
> file server. Set `SNAPDROPX_AUTH` in Vercel's environment variables too.

## ⚙️ Configuration (environment variables)

| Variable               | Default | What it does                                        |
| ---------------------- | ------- | --------------------------------------------------- |
| `SNAPDROPX_DIR`        | `.`     | Directory the server serves                         |
| `SNAPDROPX_AUTH`       | _(empty)_ | `username:password` — gates every file route    |
| `SNAPDROPX_PORT`       | `8000`  | Port for uvicorn only (Dockerfile / Procfile / Render) |
| `SNAPDROPX_MAX_UPLOAD_MB` | `100` | Per-file upload cap in MB                           |

CLI flags always override the environment: `snapdropx serve --auth a:b`
beats `SNAPDROPX_AUTH`, and `--max-upload-mb 50` beats
`SNAPDROPX_MAX_UPLOAD_MB`. Copy `.env.example` to `.env` as a starting
point (never commit a real password).

## 🔐 Authentication — how the deployed app is protected

When `SNAPDROPX_AUTH` is set (or `--auth` is passed), **every route
that touches files requires login**: `/`, `/browse/*`, `/download/*`,
`/preview/*`, `/zip/*`, `/upload`, `/delete/*`, `/mkdir`, `/rename`,
and all `/api/*` routes. An unauthenticated visitor gets the browser's
login prompt and, without valid credentials, a `401 Unauthorized`
response — no file names, no listings, no downloads.

The only public route is `/health`, which returns just
`{"status": "healthy", "version": "2.0.0"}` so platforms like Render can
run health checks. It exposes no file data.

So the deployment rule is simple: **public URL ⇒ `SNAPDROPX_AUTH`
must be set.** The included `render.yaml` already declares it as a
dashboard-set secret (`sync: false`) so it is set before the service
goes live.

## 🌐 API Endpoints
| Endpoint           | Method | Description                    |
| ------------------ | ------ | ------------------------------ |
| `/`                | GET    | List root directory            |
| `/browse/{path}`   | GET    | Browse subdirectory            |
| `/download/{path}` | GET    | Download file                  |
| `/preview/{path}`  | GET    | Preview image/text inline, else download |
| `/zip/{path}`      | GET    | Download a directory as a ZIP (empty path = root) |
| `/upload`          | POST   | Upload files (form fields `files` + `path`) |
| `/delete/{path}`   | DELETE | Delete a file or an empty directory |
| `/mkdir`           | POST   | Create a subfolder (form fields `path` + `name`) |
| `/rename`          | POST   | Rename within the same folder (JSON `{path, new_name}`) |
| `/api/files?path=` | GET    | JSON directory listing         |
| `/api/stats`       | GET    | JSON file/folder counts + total size |
| `/health`          | GET    | Health check (public)          |


## 📤 Upload via curl
Single file
curl -F "files=@file.txt" http://localhost:8000/upload

With authentication
curl -u username:password -F "files=@file.txt" http://localhost

Multiple files
curl -F "files=@a.txt" -F "files=@b.txt" http://localhost

Upload into subfolder
curl -F "files=@file.txt" -F "path=subdir" http://localhost:8000/upload

Delete a file
curl -X DELETE http://localhost:8000/delete/file.txt

Download a folder as ZIP
curl -O http://localhost:8000/zip/subdir

## 🧪 Development
Install dev dependencies
pip install -e ".[dev]"

Run tests
pytest tests/ -v

🤝 Contributing
git checkout -b feature/new-feature
git commit -m "Add new feature"
git push origin feature/new-feature

🔐 Security Notes

Credentials are never stored in code

Each user sets their own username/password at runtime

Self-signed SSL may show browser warning (expected)

📝 License
MIT License

 Author :


Made with ❤️ by Rayan.


GitHub: https://github.com/vertexcrew

