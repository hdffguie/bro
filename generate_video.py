import asyncio
import os
import sys
import time
import requests
from playwright.async_api import async_playwright

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
IMAGE_DIR = "bing_automated_images"
VIDEO_DIR = "generated_videos"

os.makedirs(VIDEO_DIR, exist_ok=True)

def read_video_prompts():
    if not os.path.exists("prompts.txt"):
        return {}
    with open("prompts.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    video_prompts = {}
    for idx, line in enumerate(lines, start=1):
        if "|" in line:
            v_prompt = line.split("|")[1].strip()
            video_prompts[idx] = v_prompt
    return video_prompts

def send_telegram_video(video_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    try:
        if os.path.exists(video_path):
            with open(video_path, "rb") as file:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"video": file}, timeout=120)
    except Exception as e:
        print(f"Telegram upload error: {e}")

async def process_image_to_video(page, image_path, image_num, motion_prompt):
    print(f"\n🎬 Processing Video #{image_num}...")

    await page.goto("https://upsampler.com/free-video-generator-no-signup", wait_until="networkidle")

    # Cookie Accept
    try:
        accept_btn = page.get_by_role("button", name="Accept")
        if await accept_btn.is_visible(timeout=3000):
            await accept_btn.click()
    except Exception:
        pass

    # 1. Upload Input Image
    file_input = page.locator("input[type='file']").first
    await file_input.set_input_files(image_path)
    print(f"📸 Uploaded Image #{image_num}")
    await asyncio.sleep(3)

    # 2. Fill Video & Voice Prompt
    prompt_input = page.get_by_placeholder("Enter a prompt to generate a video...")
    await prompt_input.fill(motion_prompt)

    # 3. Set Duration 5 seconds
    try:
        duration_dropdown = page.get_by_text("3 seconds")
        if await duration_dropdown.is_visible(timeout=2000):
            await duration_dropdown.click()
            await asyncio.sleep(1)
            await page.get_by_text("5 seconds", exact=True).click()
    except Exception:
        pass

    # 4. Click Generate with Auto Retry
    generate_btn = page.get_by_role("button", name="Generate Video", exact=True)
    gpu_error = page.get_by_text("free GPUs are in high demand", exact=False)

    started = False
    for attempt in range(1, 15):
        if await generate_btn.is_visible():
            await generate_btn.click()

        await asyncio.sleep(6)

        if await gpu_error.is_visible():
            print(f"⚠️ GPU busy (Attempt {attempt}). Retrying...")
            await asyncio.sleep(8)
            if attempt % 4 == 0:
                await page.reload(wait_until="networkidle")
                await page.locator("input[type='file']").first.set_input_files(image_path)
                await prompt_input.fill(motion_prompt)
        else:
            started = True
            break

    if not started:
        print(f"❌ Failed to start Video #{image_num}")
        return

    # 5. Download Video
    see_result_btn = page.locator("button:has-text('See result'), a:has-text('See result')").first
    video_element = page.locator("video:not([src*='_static'])").first

    start_time = time.time()
    video_ready = False

    while time.time() - start_time < 360:
        await asyncio.sleep(10)
        if await see_result_btn.is_visible():
            await see_result_btn.click()
            await asyncio.sleep(3)

        if await video_element.count() > 0 and await video_element.is_visible():
            video_ready = True
            break

    if video_ready:
        video_filename = os.path.join(VIDEO_DIR, f"Video_{image_num}.mp4")
        video_src = await video_element.get_attribute("src")

        if video_src:
            download_btn = page.locator("a:has-text('Download'), button:has-text('Download')").first
            if await download_btn.is_visible():
                async with page.expect_download() as download_info:
                    await download_btn.click()
                download = await download_info.value
                await download.save_as(video_filename)
            else:
                v_data = requests.get(video_src).content
                with open(video_filename, "wb") as f:
                    f.write(v_data)

            print(f"✅ Video #{image_num} Completed!")
            send_telegram_video(video_filename, f"🎬 Scene #{image_num} Video Ready!")

async def main():
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    total_machines = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    video_prompts = read_video_prompts()
    
    # Find existing generated images
    if not os.path.exists(IMAGE_DIR):
        print("❌ Image directory not found!")
        return

    all_images = sorted([f for f in os.listdir(IMAGE_DIR) if f.startswith("Generated_Image_") and f.endswith(".jpg")])
    
    # Machine distribution
    chunk_size = len(all_images) // total_machines + (1 if len(all_images) % total_machines != 0 else 0)
    start_idx = (machine_id - 1) * chunk_size
    end_idx = min(start_idx + chunk_size, len(all_images))
    assigned_images = all_images[start_idx:end_idx]

    print(f"🖥️ Machine {machine_id} generating {len(assigned_images)} videos.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        for img_name in assigned_images:
            img_num = int(img_name.replace("Generated_Image_", "").replace(".jpg", ""))
            img_path = os.path.join(IMAGE_DIR, img_name)
            motion_prompt = video_prompts.get(img_num, "Cinematic slow zoom in, natural dialogue speaking motion")
            
            await process_image_to_video(page, img_path, img_num, motion_prompt)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
