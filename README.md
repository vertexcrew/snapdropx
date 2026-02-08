🚀 SnapDropX

Secure · Zero-Config · Local File Drop Server

SnapDropX is a modern, secure alternative to python -m http.server with a
beautiful web UI, drag-and-drop uploads, authentication, and HTTPS support.
Perfect for quickly sharing files between machines or within a local network.

✨ Features

🔐 Secure by Default (Optional HTTP Basic Auth)

📤 Drag & Drop File Uploads

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
snapdropx /path/to/files

Custom port
snapdropx --port 8080

Enable authentication
snapdropx --auth username:password

## Browser will ask for username & password

Enable HTTPS (self-signed SSL)
snapdropx --ssl

Full secure configuration
snapdropx /data --port 8443 --auth admin:secret --ssl

Access from other devices (LAN)
snapdropx --host 0.0.0.0 --port 8000 --auth user:pass

## Open on phone / other PC:
http://YOUR_LOCAL_IP:8000

## 🌐 API Endpoints
| Endpoint           | Method | Description         |
| ------------------ | ------ | ------------------- |
| `/`                | GET    | List root directory |
| `/browse/{path}`   | GET    | Browse subdirectory |
| `/download/{path}` | GET    | Download file       |
| `/upload`          | POST   | Upload files        |
| `/health`          | GET    | Health check        |


## 📤 Upload via curl
Single file
curl -F "files=@file.txt" http://localhost:8000/upload

With authentication
curl -u username:password -F "files=@file.txt" http://localhost

Multiple files
curl -F "files=@a.txt" -F "files=@b.txt" http://localhost

Upload into subfolder
curl -F "files=@file.txt" -F "path=subdir" http://localh

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
