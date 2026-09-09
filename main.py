import os
import asyncio
import requests
from playwright.async_api import async_playwright

IMAGE_DIR = "bing_automated_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

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

        print("⏳ Waiting for image generation to complete...")
        # Bing images ko load hone mein 30-45 seconds lagte hain
        await asyncio.sleep(40)

        # Generated images ko dhoondo aur download karo
        img_elements = page.locator("img.mimg, div.img_cont img").all()
        saved_count = 0
        
        for idx, img in enumerate(await img_elements, start=1):
            src = await img.get_attribute("src")
            if src and src.startswith("http"):
                try:
                    img_data = requests.get(src).content
                    img_path = os.path.join(IMAGE_DIR, f"Generated_Image_{idx}.jpg")
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    print(f"✅ Saved base image: {img_path}")
                    saved_count += 1
                    if saved_count >= 1: # Kam se kam 1 image chahiye
                        break
                except Exception as e:
                    print(f"⚠️ Failed to download image {idx}: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
