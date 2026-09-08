import asyncio
import os
import sys
import time
import requests
from playwright.async_api import async_playwright

BOT_TOKEN = "8350328141:AAGjLVuJO6QvNb9v2NyoqbjevqNgR5WKJHk"
CHAT_ID = "8571870755"

def send_telegram_photo(image_path, caption=""):
    """Telegram pe screenshot bhejne ka function"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        if os.path.exists(image_path):
            with open(image_path, "rb") as file:
                res = requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": file}, timeout=15)
                print(f"[Telegram Photo Status]: {res.status_code}")
    except Exception as e:
        print(f"[Telegram Exception]: {e}")

def send_telegram_video(video_path, caption=""):
    """Telegram pe video bhejne ka function"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    try:
        if os.path.exists(video_path):
            with open(video_path, "rb") as file:
                res = requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"video": file}, timeout=120)
                print(f"[Telegram Video Status]: {res.status_code}")
    except Exception as e:
        print(f"[Telegram Exception]: {e}")

async def capture_and_send_status(page, prompt_num, step_description=""):
    """Screenshot lekar Telegram pe bhejne ka function"""
    path = "live_status.png"
    try:
        await page.screenshot(path=path)
        caption = f"📸 Machine #{prompt_num} | Status: {step_description}"
        send_telegram_photo(path, caption)
    except Exception as e:
        print(f"Screenshot capture failed: {e}")

async def main():
    # GitHub Runner environment variable se prompt lega
    prompt = os.getenv("PROMPT", "A cinematic shot of a futuristic city with flying cars at sunset")
    prompt_num = os.getenv("PROMPT_NUM", "1")

    print(f"\n==========================================")
    print(f"Machine Started for Prompt #{prompt_num}: {prompt}")
    print(f"==========================================")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            print("Website khol rahe hain...")
            await page.goto("https://upsampler.com/free-video-generator-no-signup", wait_until="networkidle")
            await capture_and_send_status(page, prompt_num, "Website khul gayi hai")

            # 1. Cookie Popup Accept
            try:
                accept_btn = page.get_by_role("button", name="Accept")
                await accept_btn.wait_for(timeout=5000)
                await accept_btn.click()
                print("Cookie popup accept ho gaya.")
            except Exception:
                print("Cookie popup nahi mila ya pehle se closed hai.")

            # 2. Scroll Down
            await page.evaluate("window.scrollBy(0, 300)")
            await asyncio.sleep(1)

            # 3. Prompt Add Karna
            prompt_input = page.get_by_placeholder("Enter a prompt to generate a video...")
            await prompt_input.fill(prompt)
            print(f"Prompt input add ho gaya.")

            # 4. Duration 5 Seconds Set Karna
            duration_dropdown = page.get_by_text("3 seconds")
            if await duration_dropdown.is_visible():
                await duration_dropdown.click()
                await asyncio.sleep(1)
                await page.get_by_text("5 seconds", exact=True).click()
                print("Duration 5 seconds set ho gayi.")

            await capture_and_send_status(page, prompt_num, f"Prompt '{prompt[:25]}...' aur 5s duration set hai")

            # 5. Generate Click
            generate_btn = page.get_by_role("button", name="Generate Video", exact=True)
            await generate_btn.click()
            print("Video generation start ho chuki hai...")

            # 6. Wait Loop & 'See result' Handling
            see_result_btn = page.locator("button:has-text('See result'), a:has-text('See result')").first
            video_element = page.locator("video:not([src*='_static'])").first

            start_time = time.time()
            max_wait_seconds = 300
            video_ready = False

            while time.time() - start_time < max_wait_seconds:
                await asyncio.sleep(10)

                if await see_result_btn.is_visible():
                    print("'See result' button click kar rahe hain...")
                    await capture_and_send_status(page, prompt_num, "Result Ready! 'See result' click kar rahe hain...")
                    await see_result_btn.click()
                    await asyncio.sleep(3)

                if await video_element.count() > 0 and await video_element.is_visible():
                    print("Video ready ho gayi!")
                    await capture_and_send_status(page, prompt_num, "Video screen par ready ho gayi hai!")
                    video_ready = True
                    break
                else:
                    await capture_and_send_status(page, prompt_num, "Video process ho rahi hai...")

            if not video_ready:
                raise Exception("Video generation 5 minute mein complete nahi hui.")

            # 7. Video Download & Telegram Upload
            video_filename = f"generated_video_{prompt_num}.mp4"
            video_src = await video_element.get_attribute("src")

            if video_src:
                download_btn = page.locator("a:has-text('Download'), button:has-text('Download')").first
                if await download_btn.is_visible():
                    async with page.expect_download() as download_info:
                        await download_btn.click()
                    download = await download_info.value
                    await download.save_as(video_filename)
                else:
                    video_data = requests.get(video_src).content
                    with open(video_filename, "wb") as f:
                        f.write(video_data)

                print(f"Video download ho gayi!")
                send_telegram_video(video_filename, f"✅ Video #{prompt_num} Completed!\n\n📌 Prompt: {prompt}")

        except Exception as e:
            print(f"Error Machine #{prompt_num} par: {e}")
            error_img = f"error_{prompt_num}.png"
            await page.screenshot(path=error_img)
            send_telegram_photo(error_img, f"❌ Error on Prompt #{prompt_num}: {e}")
            raise e

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
