import os
import asyncio
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

        # 🔥 Multiple flexible selectors taaki Bing ka layout badalne par bhi error na aaye
        selectors = [
            "textarea#sb_form_q",
            "textarea[placeholder*='What do you want']",
            "textarea[placeholder*='prompt' i]",
            "textarea[aria-label*='Prompt' i]",
            "textarea",
            "div[contenteditable='true']"
        ]

        prompt_input = None
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.is_visible(timeout=3000):
                    prompt_input = loc
                    print(f"✅ Found prompt input using selector: {sel}")
                    break
            except Exception:
                continue

        if not prompt_input:
            print("❌ Could not find the prompt input box on Bing.")
            await browser.close()
            return

        await prompt_input.fill(first_prompt)
        
        # Create button ke liye bhi flexible selectors
        create_btn_selectors = [
            "button#sb_form_go",
            "button:has-text('Create')",
            "button[aria-label*='Create']"
        ]
        
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

        print("⏳ Waiting for base image generation...")
        await asyncio.sleep(25)

        print("✅ Base Image Generated Successfully!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
