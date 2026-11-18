# Motivation video: animated graphics with Python

This script adds animated graphics to a talking-head video and renders the
finished video. I made it for my application video for the role of
Bildungsreferent*in at CorrelAid e.V.

Written by Ahmed Soliman with the help of Claude (Anthropic). I planned the
design and content, adjusted the settings and timings, and rendered the video
myself.

## What it does

- Adds a chapter progress bar across the top of the video.
- Slides the video to the left and a dark panel in from the right
  (split screen), and back to full frame for the last chapter.
- Shows two graphics in the panel:
  - a career path whose steps light up when they are mentioned
  - a topic matrix (eight topic areas, three levels) whose dots appear
    when each topic is mentioned
- Keeps the original audio and writes one finished MP4.

The graphics are drawn frame by frame with Pillow and NumPy; ffmpeg reads the
source video and encodes the result.

## Requirements

- Python 3.10 or newer
- `pip install -r requirements.txt`
- [ffmpeg](https://ffmpeg.org/) installed and available in the terminal

## Usage

Folder structure:

```
code/make_video.py
footage/clean_master.mp4   (your edited video, not included)
export/                    (output)
```

Run from the project folder:

```
python code/make_video.py                 # full video
python code/make_video.py still 50        # one still image at 50 s
python code/make_video.py preview 40 60   # render only 40-60 s
```

Without `footage/clean_master.mp4`, the script creates a placeholder video,
so the graphics can be tested without footage.

All timings, texts and colours are in the `SETTINGS` section at the top of
`code/make_video.py`.
