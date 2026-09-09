import os
import subprocess
import re

INPUT_DIR = "all_downloaded_videos"
OUTPUT_DIR = "final_output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def polish_and_upscale_clip(input_path, output_path):
    # FFmpeg command:
    # 1. scale=1920:1080:flags=lanczos -> 360p ko high quality HD mein sharp upscale karega
    # 2. unsharp -> video ke edges ko ekdum crisp aur clear banayega
    # 3. audio/video fades -> shuru aur ant ka sannata/pops hatayega
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", "scale=1920:1080:flags=lanczos,unsharp=5:5:1.0:5:5:0.0,fade=t=in:st=0:d=0.3,fade=t=out:st=4.7:d=0.3",
        "-af", "afade=t=in:st=0:d=0.3,afade=t=out:st=4.7:d=0.3",
        "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-c:a", "aac",
        output_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"✨ Polished & Upscaled: {os.path.basename(input_path)}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error: {e.stderr.decode()}")
        import shutil
        shutil.copy(input_path, output_path)

def main():
    if not os.path.exists(INPUT_DIR):
        print("❌ Input directory not found!")
        return

    video_files = []
    for root, dirs, files in os.walk(INPUT_DIR):
        for file in files:
            if file.endswith(".mp4"):
                video_files.append(os.path.join(root, file))

    if not video_files:
        print("❌ No video files found!")
        return

    video_files.sort(key=lambda x: natural_sort_key(os.path.basename(x)))

    polished_files = []
    print(f"Found {len(video_files)} video(s). Upgrading quality and polishing...")
    
    for idx, v_path in enumerate(video_files, start=1):
        out_path = os.path.join(OUTPUT_DIR, f"processed_{idx}.mp4")
        polish_and_upscale_clip(v_path, out_path)
        polished_files.append(out_path)

    # Saari clips ko aapas mein smooth crossfade/concat ke sath jodna
    print("🎬 Merging all clips into a cinematic Full Movie...")
    concat_list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
    
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p_file in polished_files:
            f.write(f"file '{os.path.basename(p_file)}'\n")

    full_movie_path = os.path.join(OUTPUT_DIR, "Full_Cinematic_Movie.mp4")
    merge_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_path, "-c", "copy", full_movie_path
    ]
    
    try:
        subprocess.run(merge_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ Full Cinematic Movie successfully created with High Quality!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Merge error: {e.stderr.decode()}")

    if os.path.exists(concat_list_path):
        os.remove(concat_list_path)

if __name__ == "__main__":
    main()
