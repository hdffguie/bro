import asyncio
import os
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
                requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, timeout=10)
    except Exception as e:
        print(f"Telegram photo error: {e}")

def send_telegram_video(video_path, caption=""):
    """Telegram pe generated video bhejne ka function"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    try:
        if os.path.exists(video_path):
            with open(video_path, "rb") as file:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, timeout=60)
    except Exception as e:
        print(f"Telegram video error: {e}")

async def screenshot_loop(page, stop_event):
    """Har 5 second mein live status screenshot Telegram par bhejega"""
    count = 1
    while not stop_event.is_set():
        await asyncio.sleep(5)
        if stop_event.is_set():
            break
        path = "live_status.png"
        try:
            await page.screenshot(path=path)
            send_telegram_photo(path, f"Live Status Update #{count}")
            count += 1
        except Exception as e:
            print(f"Screenshot capture error: {e}")

async def main():
    stop_event = asyncio.Event()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        # Background mein har 5 sec screenshot task shuru karo
        screenshot_task = asyncio.create_task(screenshot_loop(page, stop_event))

        try:
            print("Website khol rahe hain...")
            await page.goto("https://upsampler.com/free-video-generator-no-signup", wait_until="networkidle")

            # 1. Cookie Popup Accept karna
            try:
                accept_btn = page.get_by_role("button", name="Accept")
                await accept_btn.wait_for(timeout=5000)
                await accept_btn.click()
                print("Cookie popup accept ho gaya.")
            except Exception:
                print("Cookie popup nahi mila ya pehle se closed hai.")

            # 2. Page scroll down karna
            await page.evaluate("window.scrollBy(0, 300)")
            await asyncio.sleep(1)

            # 3. Prompt likhna
            prompt_input = page.get_by_placeholder("Enter a prompt to generate a video...")
            await prompt_input.fill("A cinematic shot of a futuristic city with flying cars at sunset")
            print("Prompt add kar diya gaya hai.")

            # 4. Duration ko 3 seconds se 5 seconds karna
            duration_dropdown = page.get_by_text("3 seconds")
            if await duration_dropdown.is_visible():
                await duration_dropdown.click()
                await asyncio.sleep(1)
                await page.get_by_text("5 seconds", exact=True).click()
                print("Duration 5 seconds set ho gayi.")

            # 5. Generate Video button click karna
            generate_btn = page.get_by_role("button", name="Generate Video", exact=True)
            await generate_btn.click()
            print("Video generation start ho chuki hai...")

            # 6. Generated Video ready hone ka wait karna
            # Dynamic filter jo default static videos ko ignore karta hai
            video_element = page.locator("video:not([src*='_static'])").first
            await video_element.wait_for(state="visible", timeout=300000)

            # 7. Video download karna
            video_src = await video_element.get_attribute("src")
            if video_src:
                download_btn = page.locator("a:has-text('Download'), button:has-text('Download')").first
                if await download_btn.is_visible():
                    async with page.expect_download() as download_info:
                        await download_btn.click()
                    download = await download_info.value
                    await download.save_as("generated_video.mp4")
                else:
                    video_data = requests.get(video_src).content
                    with open("generated_video.mp4", "wb") as f:
                        f.write(video_data)
                
                print("Video successfully download ho gayi!")
                send_telegram_video("generated_video.mp4", "✅ AAPKI VIDEO GENERATE HO GAYI HAI!")

        except Exception as e:
            print(f"Error aaya hai: {e}")
            error_img = "error_screenshot.png"
            await page.screenshot(path=error_img)
            send_telegram_photo(error_img, f"❌ Workflow Error: {e}")
            raise e

        finally:
            # Screenshot loop band karna
            stop_event.set()
            await screenshot_task
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
