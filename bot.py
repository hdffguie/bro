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
        print(f"[Telegram Photo Error]: {e}")

def send_telegram_video(video_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    try:
        if os.path.exists(video_path):
            with open(video_path, "rb") as file:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"video": file}, timeout=120)
    except Exception as e:
        print(f"[Telegram Video Error]: {e}")

async def main():
    prompt = os.getenv("PROMPT")
    prompt_num = os.getenv("PROMPT_NUM", "1")

    if not prompt:
        print("No PROMPT provided!")
        return

    # Har machine 12-12 second ke gap par chalegi
    stagger = (int(prompt_num) - 1) * 12
    if stagger > 0:
        print(f"Machine #{prompt_num} waiting {stagger}s before launch...")
        await asyncio.sleep(stagger)

    print(f"Machine Started for Prompt #{prompt_num}: {prompt}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            await page.goto("https://upsampler.com/free-video-generator-no-signup", wait_until="domcontentloaded", timeout=60000)

            # Cookie Accept
            try:
                accept_btn = page.get_by_role("button", name="Accept")
                await accept_btn.click(timeout=3000)
            except Exception:
                pass

            # Fill Prompt
            await page.evaluate("window.scrollBy(0, 300)")
            prompt_input = page.get_by_placeholder("Enter a prompt to generate a video...")
            await prompt_input.fill(prompt)

            # Duration 5s
            try:
                duration_dropdown = page.get_by_text("3 seconds")
                if await duration_dropdown.is_visible():
                    await duration_dropdown.click()
                    await page.get_by_text("5 seconds", exact=True).click()
            except Exception:
                pass

            generate_btn = page.get_by_role("button", name="Generate Video", exact=True)
            gpu_error_text = page.get_by_text("free GPUs are in high demand", exact=False)

            video_started = False
            for attempt in range(1, 35):
                print(f"Machine #{prompt_num} - Attempt {attempt} to click Generate...")
                
                try:
                    if await generate_btn.is_visible():
                        await generate_btn.click(timeout=3000, force=True)
                except Exception:
                    pass

                await asyncio.sleep(5)

                if await gpu_error_text.is_visible():
                    print(f"[GPU Busy] Machine #{prompt_num} - Retrying in 7s...")
                    await asyncio.sleep(7)
                    
                    # Har 5 failed attempts ke baad fresh page reload
                    if attempt % 5 == 0:
                        print(f"Reloading page for Machine #{prompt_num}...")
                        await page.reload(wait_until="domcontentloaded")
                        await asyncio.sleep(3)
                        await page.evaluate("window.scrollBy(0, 300)")
                        await prompt_input.fill(prompt)
                else:
                    print(f"Generation successfully started for Machine #{prompt_num}!")
                    video_started = True
                    break

            if not video_started:
                raise Exception("GPU busy error persisted after 35 attempts.")

            # Wait for Video Completion
            see_result_btn = page.locator("button:has-text('See result'), a:has-text('See result')").first
            video_element = page.locator("video:not([src*='_static'])").first

            start_time = time.time()
            video_ready = False

            while time.time() - start_time < 360:
                await asyncio.sleep(3)

                if await see_result_btn.is_visible():
                    try:
                        await see_result_btn.click(timeout=3000)
                    except Exception:
                        pass
                    await asyncio.sleep(2)

                if await video_element.count() > 0 and await video_element.is_visible():
                    video_ready = True
                    break

            if not video_ready:
                raise Exception("Video generation timed out after 6 minutes.")

            # Download Video
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
