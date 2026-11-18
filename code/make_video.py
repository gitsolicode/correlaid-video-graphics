"""
Motivation video: animated graphics and final assembly
=======================================================

Written by Ahmed Soliman with the help of Claude (Anthropic).

What this script does
- Reads your clean master video (cut in Premiere, with audio, no graphics).
- Adds a dark strip with the chapter progress bar on top (whole video).
- At the start of chapter 2, slides your video to the left and slides
  the dark chart panel in from the right.
- Shows a career path (chapter 2) and a topic matrix (chapter 3)
  in the panel; items light up at the moment they are mentioned.
- At the start of chapter 4, slides the panel out and brings your
  video back to full frame.
- Writes the finished MP4 with your original audio.

How to use it (terminal, inside the project folder)
    python code/make_video.py                 -> full video
    python code/make_video.py still 50        -> one still image at 50 s
    python code/make_video.py preview 40 60   -> only 40-60 s, for quick checks

If footage/clean_master.mp4 does not exist, the script creates a
placeholder video, so the graphics can be tested without footage.

All timings, texts and colours are in the SETTINGS section.
"""

import os
import sys
import json
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from matplotlib import font_manager

# =====================================================================
# SETTINGS
# =====================================================================

VIDEO_IN = "footage/clean_master.mp4"
VIDEO_OUT = "export/correlaid_video.mp4"

W, H, FPS = 1920, 1080, 30          # output size and frame rate

# Chapter titles and the second each chapter starts in your final cut
CHAPTERS = [
    ("Vorstellung", 0.0),
    ("Erfahrung", 12.0),
    ("Themenfelder", 46.9),
    ("Motivation", 84.87),
]

# Slide in (split screen) and slide back (full frame)
SLIDE_AT = 15.0                      # panel slides in
SLIDE_BACK_AT = CHAPTERS[3][1]       # back to full frame when chapter 4 starts
SLIDE_DUR = 0.8                      # seconds
VIDEO_OFFSET_X = 80                  # pixels: moves you further left in the split screen

# Career path (chapter 2): title, subtitle, side, second it lights up
STEPS = [
    ("Journalismus", "All Eyes Video", "left", 16.73),
    ("Unterricht und Workshops", "Sprachen und digitale Privatsphäre", "right", 23.53),
    ("KI-Videoproduktion", "18a.studio", "left", 37.53),
]

# Topic matrix (chapter 3): in CorrelAid's order.
# level: 0 = Praxiserfahrung, 1 = Grundlagen, 2 = Im Aufbau
# time: second the dot appears (when you mention the topic)
LEVELS = ["Praxiserfahrung", "Grundlagen", "Im Aufbau"]
TOPICS = [
    ("Datenmanagement", 0, 59.93),
    ("Datenerhebung und offene Daten", 1, 69.47),
    ("Datenqualität", 2, 78.33),
    ("Datenanalyse", 1, 70.3),
    ("Datenvisualisierung", 0, 51.37),
    ("Datenschutz", 1, 75.3),
    ("Wirkungsmanagement", 2, 79.3),
    ("Künstliche Intelligenz", 0, 55.63),
]

# Colours
BG = "#1C1A18"          # panel and top strip background
DOTS = "#3A3632"        # background dot grid
ACCENT = "#B5895A"      # warm brown: lit items, progress line
TEXT = "#EDE8E0"        # lit text
MUTED = "#6E675F"       # text not yet mentioned
UNLIT = "#4A4540"       # lines and dots not yet reached

# Layout
STRIP_H = 72            # height of the top strip
FADE = 0.35             # seconds for items to fade in
CROSSFADE = 0.5         # seconds between career path and matrix

# =====================================================================
# Implementation
# =====================================================================

PANEL_W = W // 2
PANEL_H = H - STRIP_H
SS = 2                  # supersampling for smooth shapes and text


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


C_BG, C_DOTS, C_ACCENT = hex_rgb(BG), hex_rgb(DOTS), hex_rgb(ACCENT)
C_TEXT, C_MUTED, C_UNLIT = hex_rgb(TEXT), hex_rgb(MUTED), hex_rgb(UNLIT)


def mix(c1, c2, a):
    """Blend colour c1 -> c2 by a (0..1)."""
    return tuple(int(round(x + (y - x) * a)) for x, y in zip(c1, c2))


def clamp(x):
    return max(0.0, min(1.0, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


# ---------- fonts ----------
def find_font(bold=False):
    prop = font_manager.FontProperties(
        family=["Inter", "Segoe UI", "Arial", "DejaVu Sans"],
        weight="bold" if bold else "normal")
    return font_manager.findfont(prop, fallback_to_default=True)


FONT_REG, FONT_BOLD = find_font(False), find_font(True)
_font_cache = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
    return _font_cache[key]


def wrap(text, fnt, max_w):
    """Split text into lines that fit max_w pixels."""
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        test = (cur + " " + w_).strip()
        if fnt.getlength(test) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


# ---------- video info ----------
def video_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", path], capture_output=True, text=True, check=True)
    return float(json.loads(out.stdout)["format"]["duration"])


def make_placeholder(path, seconds=110):
    """Create a grey test video with a silhouette and silent audio."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = Image.new("RGB", (W, H), (92, 80, 70))
    d = ImageDraw.Draw(img)
    d.ellipse((W / 2 - 110, 300, W / 2 + 110, 560), fill=(45, 40, 36))
    d.ellipse((W / 2 - 300, 620, W / 2 + 300, 1400), fill=(45, 40, 36))
    d.text((W / 2, 180), "Placeholder footage",
           font=font(40), fill=(230, 225, 215), anchor="mm")
    png = path.replace(".mp4", "_frame.png")
    img.save(png)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png,
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", str(seconds), "-r", str(FPS), "-c:v", "libx264",
         "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", path],
        check=True)
    os.remove(png)
    print(f"Created placeholder video: {path}")


# ---------- panel background (drawn once) ----------
def make_panel_bg():
    img = Image.new("RGB", (PANEL_W, PANEL_H), C_BG)
    d = ImageDraw.Draw(img)
    step = 28
    for y in range(step // 2, PANEL_H, step):
        for x in range(step // 2, PANEL_W, step):
            d.ellipse((x - 1.5, y - 1.5, x + 1.5, y + 1.5), fill=C_DOTS)
    return img


PANEL_BG = make_panel_bg()


# ---------- panel content ----------
def draw_career(d, t):
    """Two close parallel lines, branches light up when mentioned."""
    s = SS
    cx = 440 * s
    gap = 8 * s
    y0, y1 = 200 * s, 820 * s
    d.line((cx - gap, y0, cx - gap, y1), fill=C_UNLIT, width=3 * s)
    d.line((cx + gap, y0, cx + gap, y1), fill=C_UNLIT, width=3 * s)
    ys = np.linspace(310, 710, len(STEPS))
    f_title, f_sub = font(30 * s, True), font(22 * s)
    branch = 64 * s
    for (title, sub, side, t_on), y in zip(STEPS, ys):
        y = int(y * s)
        a = clamp((t - t_on) / FADE)
        line_c = mix(C_UNLIT, C_ACCENT, a)
        title_c = mix(C_MUTED, C_TEXT, a)
        sub_c = mix(C_UNLIT, C_MUTED, a) if a < 1 else (160, 152, 142)
        if side == "left":
            x_line = cx - gap
            x_end = x_line - branch
            text_x = x_end - 18 * s
            max_w = text_x - 40 * s
            anchor = "rs"
        else:
            x_line = cx + gap
            x_end = x_line + branch
            text_x = x_end + 18 * s
            max_w = PANEL_W * s - 40 * s - text_x
            anchor = "ls"
        d.line((x_line, y, x_end, y), fill=line_c, width=3 * s)
        r = 7 * s
        d.ellipse((x_line - r, y - r, x_line + r, y + r), fill=line_c)
        t_lines = wrap(title, f_title, max_w)
        s_lines = wrap(sub, f_sub, max_w)
        ty = y - 6 * s - (len(t_lines) - 1) * 38 * s
        for ln in t_lines:
            d.text((text_x, ty), ln, font=f_title, fill=title_c, anchor=anchor)
            ty += 38 * s
        sy = y + 30 * s
        for ln in s_lines:
            d.text((text_x, sy), ln, font=f_sub, fill=sub_c, anchor=anchor)
            sy += 30 * s


def draw_matrix(d, t):
    """Eight topics as rows, three level columns, dots appear when mentioned."""
    s = SS
    cols = [560 * s, 725 * s, 870 * s]
    f_head, f_row = font(20 * s, True), font(24 * s)
    head_y = 230 * s
    for name, cx in zip(LEVELS, cols):
        d.text((cx, head_y), name, font=f_head, fill=C_TEXT, anchor="ms")
    d.line((60 * s, head_y + 30 * s, 900 * s, head_y + 30 * s), fill=C_UNLIT, width=2 * s)
    row_y0, row_step = 320 * s, 66 * s
    max_w = cols[0] - 90 * s - 60 * s
    for i, (name, level, t_on) in enumerate(TOPICS):
        y = row_y0 + i * row_step
        a = clamp((t - t_on) / FADE)
        lines = wrap(name, f_row, max_w)
        ly = y + 9 * s - (len(lines) - 1) * 16 * s
        for ln in lines:
            d.text((60 * s, ly), ln, font=f_row, fill=mix(C_MUTED, C_TEXT, a), anchor="ls")
            ly += 32 * s
        if a > 0:
            r = 12 * s * (0.6 + 0.4 * ease_out(a))
            c = mix(C_BG, C_ACCENT, a)
            cx = cols[level]
            d.ellipse((cx - r, y - r, cx + r, y + r), fill=c)


def layer(draw_fn, t):
    """Draw one content layer at 2x on transparent background, scale down."""
    big = Image.new("RGBA", (PANEL_W * SS, PANEL_H * SS), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(big), t)
    return big.resize((PANEL_W, PANEL_H), Image.LANCZOS)


_panel_cache = {}


def panel_image(t):
    """Panel = background + the right content for time t (with crossfades)."""
    t3 = CHAPTERS[2][1]
    stages = [(draw_career, -1e9), (draw_matrix, t3)]

    # which stages are visible, with opacity
    visible = []
    for i, (fn, start) in enumerate(stages):
        end = stages[i + 1][1] if i + 1 < len(stages) else 1e9
        a_in = 1.0 if start < 0 else clamp((t - start) / CROSSFADE)
        a_out = 1.0 - clamp((t - end) / CROSSFADE)
        a = min(a_in, a_out)
        if a > 0:
            visible.append((fn, a))

    # cache: only redraw when something actually changes
    anim = [round(clamp((t - s_[3]) / FADE), 2) for s_ in STEPS]
    anim += [round(clamp((t - tp[2]) / FADE), 2) for tp in TOPICS]
    key = (tuple((fn.__name__, round(a, 2)) for fn, a in visible), tuple(anim))
    if key in _panel_cache:
        return _panel_cache[key]

    img = PANEL_BG.copy().convert("RGBA")
    for fn, a in visible:
        lay = layer(fn, t)
        if a < 1:
            alpha = lay.getchannel("A").point(lambda v: int(v * a))
            lay.putalpha(alpha)
        img = Image.alpha_composite(img, lay)
    arr = np.asarray(img.convert("RGB"))
    if len(_panel_cache) > 400:
        _panel_cache.clear()
    _panel_cache[key] = arr
    return arr


# ---------- top strip with progress bar ----------
def strip_image(t, total):
    img = Image.new("RGB", (W, STRIP_H), C_BG)
    d = ImageDraw.Draw(img)
    margin, gap, line_y, thick = 48, 10, 24, 4
    usable = W - 2 * margin - gap * (len(CHAPTERS) - 1)
    starts = [c[1] for c in CHAPTERS] + [total]
    x = margin
    f_lab = font(20)
    for i, (title, start) in enumerate(CHAPTERS):
        end = starts[i + 1]
        seg_w = usable * (end - start) / total
        d.rectangle((x, line_y, x + seg_w, line_y + thick), fill=C_UNLIT)
        played = clamp((t - start) / (end - start)) * seg_w
        if played > 0:
            d.rectangle((x, line_y, x + played, line_y + thick), fill=C_ACCENT)
        reached = t >= start
        d.text((x, line_y + thick + 30), title, font=f_lab,
               fill=C_TEXT if reached else C_MUTED, anchor="ls")
        x += seg_w + gap
    return np.asarray(img)


# ---------- one full frame ----------
def compose(video_frame, t, total):
    out = np.empty_like(video_frame)
    out[:] = C_BG
    if t < SLIDE_BACK_AT:
        p = ease_out((t - SLIDE_AT) / SLIDE_DUR)          # sliding in
    else:
        p = 1 - ease_out((t - SLIDE_BACK_AT) / SLIDE_DUR)  # sliding back
    shift = int(round((PANEL_W / 2 + VIDEO_OFFSET_X) * p))  # you move left
    if shift > 0:
        out[:, :W - shift] = video_frame[:, shift:]
    else:
        out[:] = video_frame
    panel_x = W - int(round(PANEL_W * p))      # panel comes in from the right
    if panel_x < W:
        panel = panel_image(t)
        vis_w = W - panel_x
        out[STRIP_H:, panel_x:] = panel[:, :vis_w]
    out[:STRIP_H] = strip_image(t, total)
    return out


# ---------- main ----------
def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if not os.path.exists(VIDEO_IN):
        make_placeholder(VIDEO_IN)
    total = video_duration(VIDEO_IN)

    mode = sys.argv[1] if len(sys.argv) > 1 else "full"
    os.makedirs("export", exist_ok=True)

    if mode == "still":
        t = float(sys.argv[2])
        frame = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(t), "-i", VIDEO_IN,
             "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
             "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True, check=True).stdout
        frame = np.frombuffer(frame, np.uint8).reshape(H, W, 3)
        out = f"export/still_{t:g}.png"
        Image.fromarray(compose(frame, t, total)).save(out)
        print(f"Saved {out}")
        return

    start, end = 0.0, total
    out_path = VIDEO_OUT
    if mode == "preview":
        start, end = float(sys.argv[2]), float(sys.argv[3])
        out_path = f"export/preview_{start:g}-{end:g}.mp4"
    dur = end - start

    reader = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", VIDEO_IN,
         "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
         "-r", str(FPS), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    writer = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-ss", str(start), "-t", str(dur), "-i", VIDEO_IN,
         "-map", "0:v", "-map", "1:a?",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_path],
        stdin=subprocess.PIPE)

    n_frames = int(round(dur * FPS))
    size = W * H * 3
    for i in range(n_frames):
        raw = reader.stdout.read(size)
        if len(raw) < size:
            break
        frame = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
        t = start + i / FPS
        writer.stdin.write(compose(frame, t, total).tobytes())
        if i % FPS == 0:
            print(f"\r{t:6.1f} s / {end:.1f} s", end="", flush=True)
    writer.stdin.close()
    writer.wait()
    reader.wait()
    print(f"\nDone: {out_path}")


if __name__ == "__main__":
    main()
