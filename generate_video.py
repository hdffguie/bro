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

def send_telegram_photo(photo_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        if os.path.exists(photo_path):
            with open(photo_path, "rb") as file:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": file}, timeout=15)
    except Exception as e:
        print(f"Telegram photo error: {e}")

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

def read_video_prompts():
    if not os.path.exists("prompts.txt"):
        return {}
    with open("prompts.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    video_prompts = {}
    for idx, line in enumerate(lines, start=1):
        if "|" in line:
            video_prompts[idx] = line.split("|")[1].strip()
        else:
            video_prompts[idx] = line.strip()
    return video_prompts

async def live_screenshot_monitor(page, machine_id, interval=8):
    shot_count = 1
    while True:
        try:
            await asyncio.sleep(interval)
            shot_path = f"live_video_m{machine_id}.png"
            await page.screenshot(path=shot_path)
            send_telegram_photo(shot_path, f"🎬 Machine {machine_id} Live Status #{shot_count} (Fresh IP)")
            shot_count += 1
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Live screenshot error: {e}")

async def main():
    # Yahan machine_id hi hamara target image number hai (jaise machine_id = 3 toh matlab Video #3)
    machine_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    video_prompts = read_video_prompts()
    
    if not os.path.exists(IMAGE_DIR):
        print("❌ Image directory not found!")
        return

    # Direct us specific image ko dhoondo jo is machine_id ke liye hai
    img_name = f"Generated_Image_{machine_id}.jpg"
    img_path = os.path.join(IMAGE_DIR, img_name)

    if not os.path.exists(img_path):
        print(f"⚠️ Image {img_name} not found for Machine {machine_id}.")
        return

    motion_prompt = video_prompts.get(machine_id, "Cinematic slow motion movement")
    print(f"🖥️ Machine {machine_id} processing ONLY Video #{machine_id} on a brand new IP.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True, viewport={'width': 1280, 'height': 720})
        page = await context.new_page()

        monitor_task = asyncio.create_task(live_screenshot_monitor(page, machine_id, interval=8))

        print(f"\n🎬 Processing Video #{machine_id}...")
        await page.goto("https://upsampler.com/free-video-generator-no-signup", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)

        try:
            accept_btn = page.get_by_role("button", name="Accept")
            if await accept_btn.is_visible(timeout=3000):
                await accept_btn.click()
        except Exception:
            pass

        file_input = page.locator("input[type='file']").first
        await file_input.set_input_files(img_path)
        await asyncio.sleep(3)

        selectors = [
            "input[placeholder*='prompt' i]",
            "textarea[placeholder*='prompt' i]",
            "input[placeholder*='Describe' i]",
            "textarea[placeholder*='Describe' i]",
            "textarea",
            "input[type='text']"
        ]
        for sel in selectors:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=2000):
                try:
                    await loc.fill(motion_prompt)
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

        gpu_error = page.get_by_text("free GPUs are in high demand", exact=False)
        ip_limit_error = page.get_by_text("used up today's free runs", exact=False)

        started = False
        for attempt in range(1, 10):
            if await generate_btn.is_visible():
                await generate_btn.click()
            await asyncio.sleep(5)

            if await ip_limit_error.is_visible():
                print(f"❌ IP Limit hit on Machine {machine_id}!")
                break
            elif await gpu_error.is_visible():
                print(f"⚠️ GPU busy, retrying...")
                await asyncio.sleep(6)
            else:
                started = True
                break

        if started:
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
                pre_video_shot = f"pre_video_m{machine_id}_v{machine_id}.png"
                await page.screenshot(path=pre_video_shot)
                send_telegram_photo(pre_video_shot, f"📸 Video #{machine_id} Ready! Downloading in 4 seconds...")
                await asyncio.sleep(4)

                video_filename = os.path.join(VIDEO_DIR, f"Video_{machine_id}.mp4")
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

                    print(f"✅ Video #{machine_id} Completed!")
                    send_telegram_video(video_filename, f"🎬 Scene #{machine_id} Video Ready!")

        monitor_task.cancel()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
