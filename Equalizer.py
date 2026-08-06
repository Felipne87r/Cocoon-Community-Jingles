import json
import os
import shutil
import subprocess
from pathlib import Path

print("Equalizer started", flush=True)

# Find ffmpeg
if os.getenv("GITHUB_ACTIONS") == "true":
    # GitHub Actions installs ffmpeg on the PATH
    FFMPEG = shutil.which("ffmpeg")
else:
    # Try PATH first
    FFMPEG = shutil.which("ffmpeg")

    # If not found, search the C: drive
    if FFMPEG is None:
        print("Searching for ffmpeg.exe...")
        FFMPEG = Path(r"C:\ffmpeg\bin\ffmpeg.exe")

if FFMPEG is None:
    raise FileNotFoundError(
        "Could not find ffmpeg.exe. Install FFmpeg or add it to your PATH."
    )

# Root folder containing your audio files
AUDIO_DIR = Path(__file__).resolve().parent

# Progress file
PROGRESS_FILE = AUDIO_DIR / "equalized_files.json"

# Audio file extensions to process
EXTENSIONS = {
    ".wav",
    ".mp3",
    ".flac",
    ".ogg",
    ".m4a",
    ".aac",
    ".wma",
    ".opus"
}

# Load previously completed files
if PROGRESS_FILE.exists():
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        completed = set(json.load(f))
else:
    completed = set()

processed = 0
skipped = 0
failed = 0

for file in AUDIO_DIR.rglob("*"):
    if not file.is_file():
        continue

    # Skip searching inside an ffmpeg folder
    if "ffmpeg" in file.parts:
        continue

    if file.suffix.lower() not in EXTENSIONS:
        continue

    # Use forward slashes so Windows/Linux produce the same JSON
    relative_path = file.relative_to(AUDIO_DIR).as_posix()

    if relative_path in completed:
        skipped += 1
        print(f"Skipping: {relative_path}")
        continue

    print(f"Processing: {relative_path}")

    # Temporary file in the same folder
    temp_file = file.with_name(file.stem + "_temp" + file.suffix)

    cmd = [
        FFMPEG,
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(file),
        "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
        str(temp_file)
    ]

    try:
        subprocess.run(cmd, check=True)
        os.replace(temp_file, file)

        completed.add(relative_path)

        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(completed), f, indent=2)

        processed += 1
        print("  [OK] Done")

    except subprocess.CalledProcessError as e:
        failed += 1
        print(f"  [FAIL] Failed: {e}")

        if temp_file.exists():
            temp_file.unlink()

print("\nFinished!")
print(f"Processed: {processed}")
print(f"Skipped:  {skipped}")
print(f"Failed:   {failed}")
