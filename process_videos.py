import os
import subprocess

INPUT_DIR = "all_downloaded_videos"
OUTPUT_DIR = "final_output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def polish_video(input_path, output_path):
    # FFmpeg command: 
    # - Audio fade-in (0.2s) & fade-out (0.2s) to remove starting/ending pops and clicks
    # - Video fade-in (0.2s) & fade-out (0.2s) for a smooth cinematic look
    # - Normalizing audio stream
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", "afade=t=in:st=0:d=0.2,afade=t=out:st=4.8:d=0.2",
        "-vf", "fade=t=in:st=0:d=0.2,fade=t=out:st=4.8:d=0.2",
        "-c:v", "libx264", "-c:a", "aac",
        output_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"✨ Successfully polished: {os.path.basename(input_path)}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ FFmpeg warning/error on {input_path}, copying original. Error: {e.stderr.decode()}")
        # Fallback: agar ffmpeg mein koi issue aaye toh original copy kar lo
        import shutil
        shutil.copy(input_path, output_path)

def main():
    if not os.path.exists(INPUT_DIR):
        print("❌ Input directory not found!")
        return

    # Subfolders ya files ko dhoondo
    video_files = []
    for root, dirs, files in os.walk(INPUT_DIR):
        for file in files:
            if file.endswith(".mp4"):
                video_files.append(os.path.join(root, file))

    print(f"Found {len(video_files)} video(s) to polish.")

    for v_path in video_files:
        filename = os.path.basename(v_path)
        out_path = os.path.join(OUTPUT_DIR, filename)
        polish_video(v_path, out_path)

if __name__ == "__main__":
    main()
