"""
download_fonts.py

Utility script to download and install key font files required for subtitle burning
(via ffmpeg/libass) and browser CSS previews.
"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

FONTS_TO_DOWNLOAD = {
    "KOMIKAX_.ttf": "https://github.com/RitzyMage/comic-cms/raw/master/comic-cms/static/fonts/KOMIKAX_.ttf",
    "Montserrat-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Regular.ttf",
    "Montserrat-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Bold.ttf",
    "Montserrat-Black.ttf": "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Black.ttf",
    "Roboto-Regular.ttf": "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Regular.ttf",
    "Roboto-Bold.ttf": "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Bold.ttf",
    "Roboto-Black.ttf": "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Black.ttf",
    "Poppins-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf",
    "Poppins-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf",
    "Poppins-Black.ttf": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Black.ttf",
    "SpaceGrotesk-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/spacegrotesk/SpaceGrotesk-Regular.ttf",
    "SpaceGrotesk-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/spacegrotesk/SpaceGrotesk-Bold.ttf",
    "Inter-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Regular.ttf",
    "Inter-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Bold.ttf",
    "Inter-Black.ttf": "https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Black.ttf",
}


def download_and_install_fonts() -> None:
    # 1. System fonts directory (for ffmpeg/libass on macOS)
    system_fonts_dir = Path("/Users/manojkc/Library/Fonts")
    system_fonts_dir.mkdir(parents=True, exist_ok=True)

    # 2. Frontend public assets folder (for browser CSS styling)
    backend_dir = Path(__file__).resolve().parents[2]
    frontend_fonts_dir = backend_dir.parent / "frontend" / "public" / "fonts"
    frontend_fonts_dir.mkdir(parents=True, exist_ok=True)

    print(f"[download_fonts] Target directories:\n  System: {system_fonts_dir}\n  Frontend: {frontend_fonts_dir}")

    for filename, url in FONTS_TO_DOWNLOAD.items():
        system_dest = system_fonts_dir / filename
        frontend_dest = frontend_fonts_dir / filename

        # Download to system folder if missing
        if not system_dest.exists():
            print(f"[download_fonts] Downloading {filename} to system fonts...")
            try:
                urllib.request.urlretrieve(url, str(system_dest))
            except Exception as e:
                print(f"[download_fonts] Failed to download {filename} to system fonts: {e}")

        # Download to frontend folder if missing
        if not frontend_dest.exists():
            print(f"[download_fonts] Downloading {filename} to frontend assets...")
            try:
                urllib.request.urlretrieve(url, str(frontend_dest))
            except Exception as e:
                print(f"[download_fonts] Failed to download {filename} to frontend assets: {e}")

    print("[download_fonts] Font downloading routine completed.")


if __name__ == "__main__":
    download_and_install_fonts()
