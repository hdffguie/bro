import asyncio
import requests
from playwright.async_api import async_playwright

# Telegram function (Use for alerts, but avoid sending every 5 seconds to avoid API Rate Limits)
def send_telegram_photo(bot_token, chat_id, photo_path, message="Status Update"):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {'chat_id': chat_id, 'caption': message}
            files = {'photo': photo}
            requests.post(url, data=payload, files=files)
    except Exception as e:
        print(f"Failed to send to Telegram: {e}")

async def run_automation():
    # APNA NAYA TOKEN YAHAN USE KAREIN (Environment Variables se lena best practice hai)
    BOT_TOKEN = "8350328141:AAGjLVuJO6QvNb9v2NyoqbjevqNgR5WKJHk" 
    CHAT_ID = "8571870755"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # GitHub Actions par headless hi chalega
        page = await browser.new_page()

        try:
            print("Navigating to website...")
            await page.goto("https://upsampler.com/free-video-generator-no-signup") # Demo URL

            print("Filling prompt...")
            # Note: Aapko inspect element karke sahi selectors dhoondhne honge
            await page.fill("textarea#prompt-input-id", "A beautiful sunset over the mountains")

            print("Selecting duration...")
            # Dropdown select karne ka tareeqa
            await page.select_option("select#duration-selector", value="5") 

            print("Clicking Generate...")
            await page.click("button.generate-btn")

            # Video generate hone ka wait karna (isme time lag sakta hai)
            print("Waiting for generation to complete...")
            # Example: Wait for download button to appear
            await page.wait_for_selector("a.download-btn", timeout=60000) # Wait up to 60 seconds

            # Download handle karna
            async with page.expect_download() as download_info:
                await page.click("a.download-btn")
            download = await download_info.value
            await download.save_as(f"generated_video.mp4")
            print("Download successful!")

        except Exception as e:
            print(f"An error occurred: {e}")
            # Error aane par screenshot lena
            error_screenshot = "error_screenshot.png"
            await page.screenshot(path=error_screenshot)
            
            # Telegram par error screenshot bhejna
            send_telegram_photo(BOT_TOKEN, CHAT_ID, error_screenshot, "Error Occurred in Script!")
            
            # GitHub Actions ko batane ke liye ki script fail hua hai, error raise karein
            raise e 
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_automation())
