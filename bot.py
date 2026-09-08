import os
import time
import requests
from gradio_client import Client

BOT_TOKEN = "8350328141:AAGjLVuJO6QvNb9v2NyoqbjevqNgR5WKJHk"
CHAT_ID = "8571870755"

# 5 Alag Public Spaces (Bina Token Ke Chalne Wale)
PUBLIC_SPACES = [
    "Lightricks/LTX-Video-Playground",
    "KingNish/LTX-Video-ZeroGPU",
    "aipicasso/LTX-Video-0.9.1",
    "Wan-Video/Wan2.1-T2V-1.3B",
    "THUDM/CogVideoX-5B-Space"
]

def send_telegram_video(video_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    try:
        if os.path.exists(video_path):
            with open(video_path, "rb") as file:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"video": file}, timeout=120)
            print("Telegram par video bhej di gayi!")
    except Exception as e:
        print(f"[Telegram Exception]: {e}")

def main():
    prompt = os.getenv("PROMPT")
    prompt_num = os.getenv("PROMPT_NUM", "1")

    if not prompt:
        print("PROMPT variable missing!")
        return

    # Machine number ke hisab se alag Space allocate karna (No Collision)
    space_index = (int(prompt_num) - 1) % len(PUBLIC_SPACES)
    target_space = PUBLIC_SPACES[space_index]

    print(f"🚀 Machine #{prompt_num} connecting to Public Space: {target_space}")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Directly connect without any HF Token
            client = Client(target_space)
            
            print(f"🎬 Video generation in progress for Machine #{prompt_num} (Attempt {attempt+1})...")
            
            # Gradio API Call
            result = client.predict(
                prompt=prompt,
                negative_prompt="worst quality, low quality, blurry",
                height=480,
                width=704,
                num_frames=121,
                frame_rate=24,
                seed=42,
                api_name="/generate_video"
            )

            video_path = result if isinstance(result, str) else result[0]
            
            # Download file locally for Artifact upload
            output_file = f"generated_video_{prompt_num}.mp4"
            if os.path.exists(video_path):
                os.rename(video_path, output_file)
            
            send_telegram_video(output_file, f"✅ Video #{prompt_num} Ready!\n📌 Source: {target_space}\n📌 Prompt: {prompt}")
            return

        except Exception as e:
            print(f"❌ Attempt {attempt+1} failed on {target_space}: {e}")
            # Switch to next space if current space is temporarily busy
            space_index = (space_index + 1) % len(PUBLIC_SPACES)
            target_space = PUBLIC_SPACES[space_index]
            time.sleep(5)

    print(f"Machine #{prompt_num} completely failed after retries.")

if __name__ == "__main__":
    main()
