import asyncio
import os
import time
import requests
from playwright.async_api import async_playwright

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

async def capture_and_send_status(page, prompt_num, step_description=""):
    path = f"live_status_{prompt_num}.png"
    try:
        await page.screenshot(path=path)
        caption = f"📸 Machine #{prompt_num} | Status: {step_description}"
        send_telegram_photo(path, caption)
    except Exception as e:
        print(f"Screenshot error: {e}")

async def main():
    prompt = os.getenv("PROMPT")
    prompt_num = os.getenv("PROMPT_NUM", "1")

    if not prompt:
        print("No PROMPT environment variable provided!")
        return

    # Staggered delay taaki Telegram messages parallelly safe bheje ja sakein
    stagger_offset = (int(prompt_num) % 5) * 2
    await asyncio.sleep(stagger_offset)

    print(f"Machine Started for Prompt #{prompt_num}: {prompt}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            await page.goto("https://upsampler.com/free-video-generator-no-signup", wait_until="domcontentloaded", timeout=60000)
            await capture_and_send_status(page, prompt_num, "Website khul gayi hai")

            # 1. Cookie Popup Accept
            try:
                accept_btn = page.get_by_role("button", name="Accept")
                await accept_btn.wait_for(timeout=4000)
                await accept_btn.click()
            except Exception:
                pass

            # 2. Scroll & Prompt Input
            await page.evaluate("window.scrollBy(0, 300)")
            prompt_input = page.get_by_placeholder("Enter a prompt to generate a video...")
            await prompt_input.fill(prompt)

            # 3. Duration 5s Select
            duration_dropdown = page.get_by_text("3 seconds")
            if await duration_dropdown.is_visible():
                await duration_dropdown.click()
                await page.get_by_text("5 seconds", exact=True).click()

            await capture_and_send_status(page, prompt_num, "Prompt & 5s Duration set")

            # 4. Generate Click with GPU High Demand Auto-Retry Loop
            generate_btn = page.get_by_role("button", name="Generate Video", exact=True)
            gpu_error_text = page.get_by_text("free GPUs are in high demand", exact=False)

            max_retries = 20
            retry_count = 0
            generation_started = False

            while retry_count < max_retries:
                retry_count += 1
                print(f"Attempt #{retry_count}: Clicking Generate Video...")
                await generate_btn.click()
                await asyncio.sleep(4)  # Check karne ke liye sleep

                # Check agar red error popup aaya hai
                if await gpu_error_text.is_visible():
                    print(f"[GPU Busy Error] Attempt {retry_count}/{max_retries}. 5 second wait karke dobara click kar rahe hain...")
                    await capture_and_send_status(page, prompt_num, f"⚠️ GPU Busy Error! Dobara Retry Click ({retry_count}/{max_retries})...")
                    await asyncio.sleep(5)
                else:
                    print("Generation successfully start ho gayi!")
                    generation_started = True
                    break

            if not generation_started:
                raise Exception("Max retry limit reach ho gayi (GPU busy error persistent).")

            # 5. Wait Loop (Har 10 second mein screenshot Telegram par bhejega)
            see_result_btn = page.locator("button:has-text('See result'), a:has-text('See result')").first
            video_element = page.locator("video:not([src*='_static'])").first

            start_time = time.time()
            max_wait_seconds = 300
            video_ready = False
            last_screenshot_time = time.time()

            while time.time() - start_time < max_wait_seconds:
                await asyncio.sleep(2)

                current_time = time.time()
                if current_time - last_screenshot_time >= 10:
                    # Retry check during generation if error pops up again
                    if await gpu_error_text.is_visible():
                        print("Mid-process GPU error detected, re-clicking generate...")
                        await generate_btn.click()

                    await capture_and_send_status(page, prompt_num, "Video process ho rahi hai...")
                    last_screenshot_time = current_time

                if await see_result_btn.is_visible():
                    await capture_and_send_status(page, prompt_num, "Result Ready! 'See result' click kar rahe hain...")
                    await see_result_btn.click()
                    await asyncio.sleep(2)

                if await video_element.count() > 0 and await video_element.is_visible():
                    await capture_and_send_status(page, prompt_num, "Video ready ho gayi!")
                    video_ready = True
                    break

            if not video_ready:
                raise Exception("Video generation 5 minute mein complete nahi hui.")

            # 6. Video Download
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

                send_telegram_video(video_filename, f"✅ Video #{prompt_num} Ready!\n📌 Prompt: {prompt}")

        except Exception as e:
            print(f"Error Machine #{prompt_num}: {e}")
            error_img = f"error_{prompt_num}.png"
            await page.screenshot(path=error_img)
            send_telegram_photo(error_img, f"❌ Error Machine #{prompt_num}: {e}")
            raise e

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
