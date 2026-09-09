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
        context = await browser.new_context(accept_downloads=True, viewport={'width': 1920, 'height': 1080})
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

        print("⏳ Waiting for images to generate...")
        
        saved_path = ""
        img_path = os.path.join(IMAGE_DIR, "Generated_Image_1.jpg")

        for _ in range(35):
            await asyncio.sleep(4)
            
            # 1. Pehle pehli generated thumbnail par click karo taակի wo badi view window mein khul jaye
            try:
                thumbnail = page.locator("div.img_cont img, img.mimg, div.card.ans img").first
                if await thumbnail.is_visible():
                    await thumbnail.click()
                    await asyncio.sleep(2)
            except Exception:
                pass

            # 2. Ab screenshot mein dikh rahe official Download button ko target karo
            try:
                # Screenshot ke anusaar download button ke paas download icon ya text hota hai
                download_btn = page.locator("a:has-text('Download'), button:has-text('Download'), [aria-label*='Download'], svg.download, button:has(svg)").filter(has_text=re.compile(r"Download", re.I)).first
                
                # Agar text se na mile toh common download icon selector try karo
                if not await download_btn.is_visible():
                    download_btn = page.locator("a[download], button[title*='Download' i]").first

                if await download_btn.is_visible():
                    async with page.expect_download() as download_info:
                        await download_btn.click()
                    download = await download_info.value
                    await download.save_as(img_path)
                    print(f"✅ Successfully downloaded original HD image: {img_path}")
                    saved_path = img_path
                    break
            except Exception as e:
                pass

            if saved_path:
                break

        # Fallback: Agar direct download trigger na ho toh high-res element screenshot le lo
        if not os.path.exists(img_path) or os.path.getsize(img_path) < 10000:
            main_img = page.locator("div.img_cont img, img.mimg").first
            if await main_img.is_visible():
                await main_img.screenshot(path=img_path)
                print("⚠️ Saved via HD element crop fallback.")

        if os.path.exists(img_path):
            send_telegram_photo(img_path, f"🎨 HD Base Image Ready!\nPrompt: {first_prompt}")

        await browser.close()

import re
if __name__ == "__main__":
    asyncio.run(main())
