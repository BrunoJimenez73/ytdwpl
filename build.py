#!/usr/bin/env python3
"""
Build script for ytdwpl.
Downloads ffmpeg/ffprobe static binaries and packages the app with PyInstaller.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
BIN_DIR = ROOT / "bin"

# ffmpeg + ffprobe sources per platform
FFMPEG_SOURCES = {
    "Windows": {
        "url": "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "subdir": "ffmpeg-master-latest-win64-gpl",
        "ffmpeg": "bin/ffmpeg.exe",
        "ffprobe": "bin/ffprobe.exe",
    },
    "Darwin": {
        "ffmpeg_url": "https://evermeet.cx/ffmpeg/ffmpeg.zip",
        "ffprobe_url": "https://evermeet.cx/ffmpeg/ffprobe.zip",
        "subdir": None,
        "ffmpeg": "ffmpeg",
        "ffprobe": "ffprobe",
    },
    "Linux": {
        "url": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
        "subdir": "ffmpeg-*-static",
        "ffmpeg": "ffmpeg",
        "ffprobe": "ffprobe",
    },
}


def _download_file(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"  already cached: {dest.name}")
        return
    print(f"  downloading {url.split('/')[-1]}...")
    resp = urlopen(url)
    with open(dest, "wb") as f:
        while chunk := resp.read(8192):
            f.write(chunk)
    print(f"  saved to {dest}")


_WANTED = {"ffmpeg.exe", "ffprobe.exe", "ffmpeg", "ffprobe"}


def _extract_zip(archive: Path, extract_to: Path, info: dict) -> None:
    with zipfile.ZipFile(archive) as zf:
        if info["subdir"]:
            import fnmatch
            members = zf.namelist()
            subdirs = {m.split("/")[0] for m in members if "/" in m}
            matches = [s for s in subdirs if fnmatch.fnmatch(s, info["subdir"])]
            sub = matches[0] if matches else "."
        else:
            sub = "."

        for member in zf.namelist():
            name = Path(member).name
            if name not in _WANTED:
                continue
            if member.startswith(sub + "/") or (sub == "." and not member.endswith("/")):
                zf.extract(member, extract_to)
                src = extract_to / member
                dst = BIN_DIR / name
                if src.is_file():
                    shutil.move(str(src), str(dst))
                    print(f"  extracted {dst.name}")


def _extract_tar(archive: Path, extract_to: Path, info: dict) -> None:
    with tarfile.open(archive) as tf:
        members = tf.getmembers()
        if info["subdir"]:
            import fnmatch
            subdirs = {m.name.split("/")[0] for m in members if "/" in m.name}
            matches = [s for s in subdirs if fnmatch.fnmatch(s, info["subdir"])]
            sub = matches[0] if matches else "."
        else:
            sub = "."

        for member in members:
            name = Path(member.name).name
            if name not in _WANTED:
                continue
            tf.extract(member, extract_to)
            src = extract_to / member.name
            dst = BIN_DIR / name
            if src.is_file():
                shutil.move(str(src), str(dst))
                print(f"  extracted {dst.name}")


def fetch_ffmpeg() -> None:
    system = platform.system()
    if system not in FFMPEG_SOURCES:
        print(f"Unsupported platform: {system}")
        print("Install ffmpeg manually and ensure it's in PATH.")
        return

    info = FFMPEG_SOURCES[system]
    BIN_DIR.mkdir(parents=True, exist_ok=True)

    cache_dir = ROOT / ".build-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if system == "Darwin":
        # macOS: separate downloads for ffmpeg and ffprobe
        for tool, url_key in [("ffmpeg", "ffmpeg_url"), ("ffprobe", "ffprobe_url")]:
            url = info[url_key]
            archive_name = url.split("/")[-1]
            archive_path = cache_dir / archive_name
            _download_file(url, archive_path)

            extract_to = cache_dir / "extract"
            if extract_to.exists():
                shutil.rmtree(extract_to)
            extract_to.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(archive_path) as zf:
                for member in zf.namelist():
                    name = Path(member).name
                    if name == tool:
                        zf.extract(member, extract_to)
                        src = extract_to / member
                        dst = BIN_DIR / name
                        if src.is_file():
                            shutil.move(str(src), str(dst))
                            print(f"  extracted {dst.name}")

            shutil.rmtree(extract_to, ignore_errors=True)
    else:
        # Windows/Linux: single archive with both
        archive_name = info["url"].split("/")[-1]
        archive_path = cache_dir / archive_name
        _download_file(info["url"], archive_path)

        extract_to = cache_dir / "extract"
        if extract_to.exists():
            shutil.rmtree(extract_to)
        extract_to.mkdir(parents=True, exist_ok=True)

        if archive_name.endswith(".zip"):
            _extract_zip(archive_path, extract_to, info)
        else:
            _extract_tar(archive_path, extract_to, info)

        shutil.rmtree(extract_to, ignore_errors=True)

    # Verify
    ffmpeg_exe = info["ffmpeg"].split("/")[-1]
    ffprobe_exe = info["ffprobe"].split("/")[-1]
    ffmpeg_path = BIN_DIR / ffmpeg_exe
    ffprobe_path = BIN_DIR / ffprobe_exe
    ok = ffmpeg_path.exists() and ffprobe_path.exists()
    if ok:
        print(f"\nOK: ffmpeg ready at {ffmpeg_path}")
        print(f"OK: ffprobe ready at {ffprobe_path}")
    else:
        print(f"\nWARN: ffmpeg/ffprobe not found at expected paths")
        print(f"  ffmpeg: {ffmpeg_path} ({'found' if ffmpeg_path.exists() else 'MISSING'})")
        print(f"  ffprobe: {ffprobe_path} ({'found' if ffprobe_path.exists() else 'MISSING'})")
        print("  Install ffmpeg manually and place it in bin/")


def pack_app(onefile: bool = False) -> None:
    fetch_ffmpeg()

    print("\nPackaging with PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "ytdwpl",
        "--add-data", f"{BIN_DIR}{os.pathsep}bin",
        "--add-data", f"{ROOT / 'app'}{os.pathsep}app",
        "--hidden-import", "app.db",
        "--hidden-import", "app.core.models",
        "--hidden-import", "app.core.downloader",
        "--hidden-import", "app.core.queue",
        "--hidden-import", "app.ui.layout",
        "--hidden-import", "app.ui.queue_table",
        "--hidden-import", "app.ui.progress_card",
        "--hidden-import", "app.ui.add_dialog",
        "--noconfirm",
    ]
    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    cmd.append(str(ROOT / "app" / "main.py"))

    os.chdir(ROOT)
    import subprocess
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"\nOK  Package built in dist/ytdwpl/")
    else:
        print(f"\nFAIL  PyInstaller failed (code {result.returncode})")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ytdwpl")
    parser.add_argument("--ffmpeg", action="store_true", help="Download ffmpeg only")
    parser.add_argument("--pack", action="store_true", help="Download ffmpeg + package app")
    parser.add_argument("--onefile", action="store_true", help="Package as single .exe")
    args = parser.parse_args()

    if args.ffmpeg:
        fetch_ffmpeg()
    elif args.pack:
        pack_app(onefile=args.onefile)
    else:
        fetch_ffmpeg()
        pack_app(onefile=args.onefile)


if __name__ == "__main__":
    main()
