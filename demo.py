#!/usr/bin/env python3
"""Demo script to showcase SnapDropX features."""

import tempfile
from pathlib import Path


def create_demo_files(demo_dir: Path):
    """Create demo files and directories."""
    print("📁 Creating demo files...")

    # Create various file types
    (demo_dir / "README.txt").write_text(
        "Welcome to SnapDropX Demo!\n\n"
        "This directory contains sample files to demonstrate SnapDropX features.\n"
    )

    (demo_dir / "document.txt").write_text("Sample document content")
    (demo_dir / "data.json").write_text('{"demo": true, "version": "1.0"}')
    (demo_dir / "script.py").write_text("print('Hello from SnapDropX!')")

    # Create subdirectories
    (demo_dir / "images").mkdir()
    (demo_dir / "images" / "info.txt").write_text("Image directory")

    (demo_dir / "documents").mkdir()
    (demo_dir / "documents" / "report.txt").write_text("Annual report content")

    (demo_dir / "downloads").mkdir()
    (demo_dir / "downloads" / "README.txt").write_text("Download folder")

    print(f"✅ Created demo files in {demo_dir}")


def print_usage_examples():
    """Print usage examples."""
    print("\n" + "=" * 60)
    print("🚀 SNAPDROPX USAGE EXAMPLES")
    print("=" * 60)
    print()

    print("Basic usage:")
    print("  snapdropx                          # Serve current directory")
    print("  snapdropx /path/to/files          # Serve specific directory")
    print()

    print("With security:")
    print("  snapdropx --auth admin:password    # Enable authentication")
    print("  snapdropx --ssl                    # Enable HTTPS")
    print("  snapdropx --auth user:pass --ssl   # Both auth and HTTPS")
    print()

    print("Custom configuration:")
    print("  snapdropx --port 8080              # Custom port")
    print("  snapdropx --host 0.0.0.0           # Bind to all interfaces")
    print()

    print("Upload files via curl:")
    print("  curl -F 'files=@myfile.txt' http://localhost:8000/upload")
    print("  curl -u user:pass -F 'files=@file.txt' http://localhost:8000/upload")
    print()

    print("=" * 60)


def main():
    """Run the demo."""
    print("\n🎯 SnapDropX Demo\n")

    # Create temporary demo directory
    with tempfile.TemporaryDirectory() as tmpdir:
        demo_dir = Path(tmpdir)
        create_demo_files(demo_dir)

        print_usage_examples()

        print("\n📋 Demo directory structure:")
        print(f"\n{demo_dir}/")

        for item in sorted(demo_dir.rglob("*")):
            if item.is_file():
                rel_path = item.relative_to(demo_dir)
                indent = "  " * (len(rel_path.parts) - 1)
                print(f"{indent}├── {item.name}")

        print("\n" + "=" * 60)
        print("💡 To try SnapDropX:")
        print("=" * 60)

        print(f"\n1. Open a terminal in the demo directory:")
        print(f"   cd {demo_dir}")

        print("\n2. Start SnapDropX:")
        print("   snapdropx")

        print("\n3. Open your browser to:")
        print("   http://localhost:8000")

        print("\n4. Try uploading files via drag-and-drop!")

        print("\n" + "=" * 60)

        input("\n⏸️  Press Enter to exit demo...")


if __name__ == "__main__":
    main()
