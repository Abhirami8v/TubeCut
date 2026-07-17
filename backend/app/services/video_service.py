def download_video(url: str, logger: JobLogger | None = None) -> DownloadResult:
    from pytubefix import YouTube
    from pytubefix.cli import on_progress

    if logger:
        logger.info(f"Downloading via pytubefix with OAuth: {url}")

    try:
        yt = YouTube(
            url,
            on_progress_callback=on_progress,
            use_oauth=True,
            allow_oauth_cache=True,
            client="WEB",
        )

        title = yt.title
        duration = float(yt.length or 0)
        video_id = yt.video_id

        if logger:
            logger.info(f"Video found: '{title}' ({duration:.0f}s)")

        stream = (
            yt.streams
            .filter(progressive=True, file_extension="mp4")
            .order_by("resolution")
            .last()
        )

        if not stream:
            stream = yt.streams.filter(file_extension="mp4").first()

        if not stream:
            raise RuntimeError("No downloadable stream found")

        output_path = DOWNLOADS_DIR / f"{video_id}.mp4"

        stream.download(
            output_path=str(DOWNLOADS_DIR),
            filename=f"{video_id}.mp4"
        )

        if logger:
            logger.info(f"Download complete: {output_path}")

        return {
            "video_id": video_id,
            "title": title,
            "file_path": str(output_path),
            "duration": duration,
        }

    except Exception as e:
        if logger:
            logger.error(f"pytubefix failed: {e}")

        # Fallback to yt-dlp
        if logger:
            logger.info("Trying yt-dlp fallback...")
        return _download_with_ytdlp(url, logger=logger)


def _download_with_ytdlp(url: str, logger: JobLogger | None = None) -> DownloadResult:
    import yt_dlp
    from app.core.config import PROXY_URL

    video_id = _extract_video_id(url)

    ydl_opts = {
        "outtmpl": str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
            }
        },
    }

    if PROXY_URL:
        ydl_opts["proxy"] = PROXY_URL
        if logger:
            logger.info(f"Using proxy for yt-dlp")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        if not file_path.endswith(".mp4"):
            base = file_path.rpartition(".")[0]
            file_path = f"{base}.mp4"

    if logger:
        logger.info(f"yt-dlp download complete: {file_path}")

    return {
        "video_id": info["id"],
        "title": info.get("title", "Untitled"),
        "file_path": file_path,
        "duration": float(info.get("duration") or 0.0),
    }