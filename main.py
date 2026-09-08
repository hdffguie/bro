import asyncio
import requests
from playwright.async_api import async_playwright

# Apna naya Telegram Token aur Chat ID yahan daalein
BOT_TOKEN = "8350328141:AAGjLVuJO6QvNb9v2NyoqbjevqNgR5WKJHk" 
CHAT_ID = "8571870755"

def send_telegram_photo(bot_token, chat_id, photo_path, message="Update"):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {'chat_id': chat_id, 'caption': message}
            files = {'photo': photo}
            response = requests.post(url, data=payload, files=files)
            if response.status_code != 200:
                print(f"Telegram API Error: {response.text}")
    except Exception as e:
        print(f"Failed to send to Telegram: {e}")

# Yeh function background mein chalta rahega
async def background_screenshot_loop(page):
    counter = 1
    try:
        while True:
            await asyncio.sleep(8) # Har 8 second ka wait
            print(f"Taking 8-second screenshot #{counter}...")
            shot_path = f"loop_shot_{counter}.png"
            await page.screenshot(path=shot_path)
            send_telegram_photo(BOT_TOKEN, CHAT_ID, shot_path, f"Screenshot {counter} (8s interval)")
            counter += 1
    except asyncio.CancelledError:
        # Jab main script khatam hoga, tab yeh task cancel ho jayega
        print("Background screenshot loop stopped.")

async def run_automation():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Background loop ko start karna, bina aage ka code roke
        screenshot_task = asyncio.create_task(background_screenshot_loop(page))

        try:
            print("Navigating to website...")
            # Yahan apna target URL daalein
            await page.goto("https://upsampler.com/free-video-generator-no-signup", wait_until="networkidle")

            # 1. Cookie Popup ko "Accept" karna
            print("Looking for cookie popup...")
            try:
                # Yeh sirf tabhi click karega jab "Accept" button screen par dikhega
                # Agar button ka text kuch aur hai (jaise "I Agree"), toh use change karein
                accept_button = page.get_by_text("Accept", exact=True)
                await accept_button.wait_for(timeout=5000) # 5 second tak wait karega
                await accept_button.click()
                print("Cookie popup accepted.")
            except Exception:
                print("No cookie popup found or it timed out. Moving on...")

            # 2. Page ko niche scroll karna taaki baaki options dikhein
            print("Scrolling down...")
            # 500 pixels niche scroll karega. Zarurat ke hisaab se number badal sakte hain.
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(2) # Scroll ke baad UI load hone ke liye thoda wait

            # 3. Prompt likhna (YAHAN ASLI SELECTOR DAALNA PADEGA)
            print("Filling prompt...")
            # Example: await page.fill('textarea[placeholder="Enter a prompt..."]', "My video prompt")
            await page.fill("<textarea class="flex h-20 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none" id="prompt-input" placeholder="Enter a prompt to generate a video..." rows="4"></textarea>", "A beautiful futuristic city")

            # 4. Duration change karna (YAHAN ASLI SELECTOR DAALNA PADEGA)
            print("Changing duration...")
            # Dropdown handle karne ka ek tarika:
            # await page.locator('select.duration-dropdown').select_option(value="5")
            
            # Agar wo asli select box nahi hai (balki div se banaya gaya dropdown hai), toh aise click karein:
            # await page.click("REPLACE_WITH_DROPDOWN_CLICK_SELECTOR")
            # await page.click("REPLACE_WITH_5_SECONDS_OPTION_SELECTOR")

            # 5. Generate button click karna (YAHAN ASLI SELECTOR DAALNA PADEGA)
            print("Clicking Generate...")
            await page.click("REPLACE_WITH_GENERATE_BUTTON_SELECTOR")

            # 6. Video process hone ka wait karna (Isme time lagega)
            print("Waiting for video to generate...")
            # Jab tak download button nahi aata, wait karega (max 120 sec)
            await page.wait_for_selector("REPLACE_WITH_DOWNLOAD_BUTTON_SELECTOR", timeout=120000)

            print("Job Done! Taking final screenshot.")
            await page.screenshot(path="final_success.png")
            send_telegram_photo(BOT_TOKEN, CHAT_ID, "final_success.png", "Process Complete!")

        except Exception as e:
            print(f"An error occurred: {e}")
            await page.screenshot(path="error.png")
            send_telegram_photo(BOT_TOKEN, CHAT_ID, "error.png", f"Error: {e}")
            raise e 
            
        finally:
            # Sabse zaroori: Background loop ko band karna, nahi toh script atka rahega
            screenshot_task.cancel()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_automation())
