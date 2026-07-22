# TubeCut

## Overview

TubeCut is an AI-assisted video editing application designed to simplify the process of converting long-form videos into concise, shareable clips. The application combines speech transcription, subtitle generation, caption editing, and video processing into a single workflow, allowing users to create short-form content with minimal manual effort.

## Features

* Upload videos from a local device or provide a YouTube link.
* Generate AI-based transcriptions from video audio.
* Create timestamped subtitles automatically.
* Edit captions before exporting.
* Process videos with embedded subtitles.
* Download the final processed video.
* Simple and responsive user interface.

## Technology Stack

### Frontend

* React.js
* JavaScript
* HTML
* CSS

### Backend

* Python
* FastAPI

### AI and Video Processing

* OpenAI API
* Whisper / Gemini Transcription
* FFmpeg

## Project Structure

```text
TubeCut/
├── frontend/
├── backend/
└── storage/
```

## Installation

### Clone the repository

```bash
git clone https://github.com/Abhirami8v/TubeCut.git
cd TubeCut
```

### Install the frontend

```bash
cd frontend
npm install
```

### Install the backend

```bash
cd ../backend
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file inside the backend directory and add the required API keys and configuration values.

### Run the backend

```bash
uvicorn main:app --reload
```

### Run the frontend

```bash
cd ../frontend
npm run dev
```

## How It Works

1. Upload a video or provide a YouTube URL.
2. The backend processes the media and extracts the audio.
3. The transcription service converts speech into text.
4. Captions are generated with timestamps and can be edited.
5. FFmpeg renders the final video with subtitles.
6. Processed files are stored in the `storage` directory for download.

## Future Improvements

* Support for multiple languages.
* Automatic highlight detection.
* Additional subtitle customization options.
* Cloud-based processing for improved scalability.

## Author

**Abhirami V**

## License

This project was developed for educational and learning purposes.
"# TRIAL" 
