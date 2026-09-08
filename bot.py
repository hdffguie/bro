import os
import time
import random
import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = "8350328141:AAGjLVuJO6QvNb9v2NyoqbjevqNgR5WKJHk"
CHAT_ID = "8571870755"

def send_telegram_photo(image_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as file:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": file}, timeout=15)
    except Exception as e:
        print(f"[Telegram Photo Exception]: {e}")

def send_telegram_video(video_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    try:
        if os.path.exists(video_path):
            with open(video_path, "rb") as file:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"video": file}, timeout=120)
    except Exception as e:
        print(f"[Telegram Video Exception]: {e}")

def capture_and_send_status(page, prompt_num, step_description=""):
    path = f"live_status_{prompt_num}.png"
    try:
        page.screenshot(path=path)
        caption = f"📸 Machine #{prompt_num} | Status: {step_description}"
        send_telegram_photo(path, caption)
    except Exception as e:
        print(f"Screenshot error: {e}")

def human_type(element, text):
    """Anti-bot human typing simulation"""
    element.click()
    time.sleep(random.uniform(0.6, 1.2))
    for char in text:
        element.type(char, delay=random.randint(90, 240))
    time.sleep(random.uniform(0.8, 1.5))

def run_automation():
    prompt_text = os.getenv("PROMPT", "A cinematic shot of a majestic lion walking through a futuristic glowing city at night")
    prompt_num = os.getenv("PROMPT_NUM", "1")
    url = "https://pixelbin.io/ai-tools/video-generator"

    # Multi-machine staggered launch
    stagger_offset = (int(prompt_num) - 1) * 10
    if stagger_offset > 0:
        print(f"Machine #{prompt_num} waiting {stagger_offset} seconds...")
        time.sleep(stagger_offset)

    with sync_playwright() as p:
        # Headless mode for GitHub Actions compatibility
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars"
            ]
        )
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US"
        )
        
        page = context.new_page()

        try:
            print(f"Machine #{prompt_num} - Opening URL...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(10)
            capture_and_send_status(page, prompt_num, "Website loaded successfully")

            # 1. Prompt Input with Human Typing
            print(f"Machine #{prompt_num} - Entering prompt...")
            prompt_box = page.locator("textarea[placeholder*='Describe your video']")
            prompt_box.wait_for(state="visible", timeout=15000)
            
            prompt_box.hover()
            human_type(prompt_box, prompt_text)
            capture_and_send_status(page, prompt_num, "Prompt entered via human typing")

            # 2. Click Generate Button
            print(f"Machine #{prompt_num} - Clicking Generate...")
            generate_btn = page.get_by_role("button", name="Generate", exact=True).first
            generate_btn.wait_for(state="visible", timeout=10000)
            
            generate_btn.hover()
            time.sleep(random.uniform(1.0, 2.0))
            generate_btn.click()
            capture_and_send_status(page, prompt_num, "Generate button clicked")

            # 3. Wait for Video Generation
            print(f"Machine #{prompt_num} - Waiting for video generation...")
            generated_video = page.locator("video:not([src*='dummy-cloudname'])").first
            
            try:
                generated_video.wait_for(state="visible", timeout=180000)
            except Exception:
                generated_video = page.locator("video[src^='blob:'], video[src*='pixelbin']").last
                generated_video.wait_for(state="visible", timeout=10000)

            capture_and_send_status(page, prompt_num, "Video generation completed")
            time.sleep(3)

            # 4. Save & Download Video
            video_filename = f"generated_video_{prompt_num}.mp4"
            download_btn = page.locator("button:has-text('Download'), a:has-text('Download')").first
            
            if download_btn.is_visible():
                with page.expect_download(timeout=15000) as download_info:
                    download_btn.click()
                download = download_info.value
                download.save_as(video_filename)
                print(f"SUCCESS: Saved via Download button -> {video_filename}")
            else:
                video_src = generated_video.get_attribute("src")
                if video_src:
                    response = page.request.get(video_src)
                    with open(video_filename, "wb") as f:
                        f.write(response.body())
                    print(f"SUCCESS: Saved via URL -> {video_filename}")
                else:
                    raise Exception("Video URL not found.")

            # Send Video to Telegram
            send_telegram_video(video_filename, f"✅ Video #{prompt_num} Ready!\n📌 Prompt: {prompt_text}")

        except Exception as e:
            print(f"Error Machine #{prompt_num}: {e}")
            error_img = f"error_{prompt_num}.png"
            try:
                page.screenshot(path=error_img)
                send_telegram_photo(error_img, f"❌ Machine #{prompt_num} Error: {e}")
            except Exception:
                pass
            raise e

        finally:
            browser.close()

if __name__ == "__main__":
    run_automation()
