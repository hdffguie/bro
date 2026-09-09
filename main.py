import os
import asyncio
import requests
from playwright.async_api import async_playwright

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
IMAGE_DIR = "bing_automated_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

def send_telegram_photo(photo_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        if os.path.exists(photo_path):
            with open(photo_path, "rb") as file:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": file}, timeout=15)
            print("📤 Sent base image to Telegram!")
    except Exception as e:
        print(f"Telegram photo error: {e}")

async def main():
    if not os.path.exists("prompts.txt"):
        print("❌ prompts.txt not found!")
        return

    with open("prompts.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if not lines:
        print("❌ No prompts found in prompts.txt!")
        return

    first_prompt = lines[0].replace("[IMAGE]", "").replace("[VIDEO]", "").strip()
    print(f"🎨 Generating Base Image with prompt: {first_prompt}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 720})
        page = await context.new_page()

        await page.goto("https://www.bing.com/create", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        selectors = [
            "textarea#sb_form_q",
            "textarea[placeholder*='What do you want']",
            "textarea[placeholder*='prompt' i]",
            "textarea",
            "div[contenteditable='true']"
        ]

        prompt_input = None
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.is_visible(timeout=3000):
                    prompt_input = loc
                    break
            except Exception:
                continue

        if not prompt_input:
            print("❌ Could not find prompt input box.")
            await browser.close()
            return

        await prompt_input.fill(first_prompt)
        
        create_btn_selectors = ["button#sb_form_go", "button:has-text('Create')"]
        create_btn = None
        for sel in create_btn_selectors:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=3000):
                create_btn = loc
                break

        if create_btn:
            await create_btn.click()
        else:
            await page.keyboard.press("Enter")

        print("⏳ Waiting for images to generate on Bing...")
        
        # 🔥 Smart waiting loop: Jab tak images page par show nahi hoti, tab tak wait karo (max 90 seconds)
        saved_path = ""
        for _ in range(30):
            await asyncio.sleep(3)
            # Bing image results ke alag-alag possible selectors
            img_elements = page.locator("div.img_cont img, img.mimg, div.card.ans img").all()
            if len(await img_elements) > 0:
                for idx, img in enumerate(await img_elements, start=1):
                    src = await img.get_attribute("src")
                    if src and src.startswith("http") and "bing.com" in src:
                        try:
                            # Thumbnail ki jagah high quality image link lene ki koshish
                            hq_src = src.split("?")[0] + "?w=1024&h=1024&c=1&pid=ImgGn"
                            img_data = requests.get(hq_src).content
                            if len(img_data) > 10000: # Ensure it's a valid image
                                img_path = os.path.join(IMAGE_DIR, f"Generated_Image_{idx}.jpg")
                                with open(img_path, "wb") as f:
                                    f.write(img_data)
                                print(f"✅ Successfully downloaded base image: {img_path}")
                                saved_path = img_path
                                break
                        except Exception as e:
                            print(f"⚠️ Error downloading image: {e}")
                if saved_path:
                    break

        # Agar upar wale se image nahi mili toh page ka fallback screenshot le lo taaki debugging asan ho
        if not saved_path:
            fallback_path = os.path.join(IMAGE_DIR, "Generated_Image_1.jpg")
            await page.screenshot(path="bing_debug.png", full_page=True)
            print("⚠️ Direct image fetch failed, taking fallback screenshot...")
            # Agar debug screenshot pada hai toh usey hi copy karke as image use kar lenge
            if os.path.exists("bing_debug.png"):
                import shutil
                shutil.copy("bing_debug.png", fallback_path)
                saved_path = fallback_path

        if saved_path and os.path.exists(saved_path):
            send_telegram_photo(saved_path, f"🎨 Base Foundation Image Ready!\nPrompt: {first_prompt}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
