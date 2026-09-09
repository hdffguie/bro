import asyncio
import os
import sys
import time
import requests
import subprocess
from playwright.async_api import async_playwright

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
VIDEO_DIR = "generated_videos"
IMAGE_DIR = "bing_automated_images"

os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

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

def extract_last_frame(video_path, output_image_path):
    cmd = [
        "ffmpeg", "-y", "-sseof", "-0.1", "-i", video_path,
        "-update", "1", "-q:v", "1", output_image_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"📸 Extracted last frame to {output_image_path}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error extracting last frame: {e.stderr.decode()}")

async def main():
    step_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    if not os.path.exists("prompts.txt"):
        return

    with open("prompts.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    video_prompts = [l.replace("[VIDEO]", "").replace("[IMAGE]", "").strip() for l in lines[1:]]
    
    if step_num > len(video_prompts):
        return

    current_prompt = video_prompts[step_num - 1]
    print(f"🎬 Processing Video Step {step_num}: {current_prompt}")

    input_image = ""
    if step_num == 1:
        if os.path.exists(IMAGE_DIR):
            all_imgs = sorted([os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('jpg', 'jpeg', 'png'))])
            if all_imgs:
                input_image = all_imgs[0]
        
        if not input_image or not os.path.exists(input_image):
            print(f"❌ No base image found inside '{IMAGE_DIR}' folder for Step 1!")
            return
    else:
        input_image = f"chain_frame_{step_num - 1}.jpg"
        if not os.path.exists(input_image):
            print(f"❌ Previous chained frame {input_image} not found!")
            return

    print(f"🖼️ Using Input Image: {input_image} on fresh IP.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True, viewport={'width': 1280, 'height': 720})
        page = await context.new_page()

        await page.goto("https://upsampler.com/free-video-generator-no-signup", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)

        try:
            accept_btn = page.get_by_role("button", name="Accept")
            if await accept_btn.is_visible(timeout=3000):
                await accept_btn.click()
        except Exception:
            pass

        file_input = page.locator("input[type='file']").first
        await file_input.set_input_files(input_image)
        await asyncio.sleep(3)

        selectors = [
            "input[placeholder*='prompt' i]",
            "textarea[placeholder*='prompt' i]",
            "textarea",
            "input[type='text']"
        ]
        for sel in selectors:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=2000):
                try:
                    await loc.fill(current_prompt)
                    break
                except Exception:
                    continue

        try:
            duration_dropdown = page.get_by_text("3 seconds")
            if await duration_dropdown.is_visible(timeout=2000):
                await duration_dropdown.click()
                await asyncio.sleep(1)
                await page.get_by_text("5 seconds", exact=True).click()
        except Exception:
            pass

        generate_btn = page.get_by_role("button", name="Generate Video", exact=True)
        if not await generate_btn.is_visible(timeout=3000):
            generate_btn = page.locator("button:has-text('Generate')").first

        started = False
        for attempt in range(1, 10):
            if await generate_btn.is_visible():
                await generate_btn.click()
            await asyncio.sleep(5)
            if not await page.get_by_text("used up today's free runs", exact=False).is_visible():
                started = True
                break

        if not started:
            return

        see_result_btn = page.locator("button:has-text('See result'), a:has-text('See result')").first
        video_element = page.locator("video:not([src*='_static'])").first

        start_time = time.time()
        video_ready = False
        while time.time() - start_time < 360:
            await asyncio.sleep(4)
            if await see_result_btn.is_visible():
                await see_result_btn.click()
                await asyncio.sleep(2)
            if await video_element.count() > 0 and await video_element.is_visible():
                video_ready = True
                break

        if video_ready:
            video_filename = os.path.join(VIDEO_DIR, f"Video_Step_{step_num}.mp4")
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

            print(f"✅ Video Step {step_num} Completed!")
            send_telegram_video(video_filename, f"🎬 Scene #{step_num} Ready!")
            extract_last_frame(video_filename, f"chain_frame_{step_num}.jpg")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
