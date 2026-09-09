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

        await page.goto("https://www.bing.com/create", wait_until="domcontentloaded")
        await asyncio.sleep(5)

        prompt_input = page.locator("textarea#sb_form_q, textarea[placeholder*='prompt']").first
        await prompt_input.fill(first_prompt)
        
        create_btn = page.locator("button#sb_form_go, button:has-text('Create')").first
        await create_btn.click()
        print("⏳ Waiting for base image generation...")
        await asyncio.sleep(25)

        print("✅ Base Image Generated Successfully!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
