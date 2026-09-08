import asyncio
import os
import argparse
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
    except Exception as e:
        print(f"Telegram photo error: {e}")

def read_prompts():
    if not os.path.exists("prompts.txt"):
        return []
    with open("prompts.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    prompts = []
    for line in lines:
        if "|" in line:
            image_prompt = line.split("|")[0].strip()
            if image_prompt and image_prompt[0].isdigit() and "." in image_prompt[:4]:
                image_prompt = image_prompt.split(".", 1)[1].strip()
            prompts.append(image_prompt)
    return prompts

# Live monitor interval increased to 30 seconds to prevent Telegram spam
async def live_screenshot_monitor(page, machine_id, interval=30):
    shot_count = 1
    while True:
        try:
            await asyncio.sleep(interval)
            shot_path = f"live_status_m{machine_id}.png"
            await page.screenshot(path=shot_path)
            send_telegram_photo(shot_path, f"📸 Machine {machine_id} - Live Status #{shot_count}")
            shot_count += 1
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Live screenshot error: {e}")

async def generate_bing_image(page, prompt, image_index):
    print(f"🎨 Generating Image #{image_index}: {prompt[:50]}...")
    
    try:
        await page.goto("https://www.bing.com/images/create", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)

        # Locate Text Area
        textbox = page.get_by_placeholder("Describe the image you want to create")
        if not await textbox.is_visible(timeout=5000):
            textbox = page.locator("#sb_form_q, textarea").first

        await textbox.fill(prompt)
        await asyncio.sleep(1)

        # Locate Generate Button
        gen_btn = page.get_by_role("button", name="Generate", exact=True)
        if not await gen_btn.is_visible(timeout=5000):
            gen_btn = page.locator("#create_btn_div, button:has-text('Create')").first

        await gen_btn.click()
        print(f"⏳ Clicked Generate for Image #{image_index}. Waiting for image...")

        # Wait for generated image elements directly
        img_selector = "img[src*='th?id='], .mimg, img[src*='bing.net'], img[src*='tse']"
        await page.wait_for_selector(img_selector, timeout=120000)
        await asyncio.sleep(5)

        # Extract high quality direct image URL without clicking preview
        images = page.locator(img_selector)
        count = await images.count()

        img_url = None
        for i in range(count):
            src = await images.nth(i).get_attribute("src")
            if src and ("th?id=" in src or "bing.net" in src or "tse" in src):
                # Clean URL parameters for high quality
                img_url = src.split("&w=")[0] if "&w=" in src else src
                break

        if img_url:
            response = await page.request.get(img_url)
            img_bytes = await response.body()
            img_path = os.path.join(IMAGE_DIR, f"Generated_Image_{image_index}.jpg")
            with open(img_path, "wb") as f:
                f.write(img_bytes)
            print(f"✅ Image #{image_index} Saved successfully!")
            send_telegram_photo(img_path, f"✅ Generated Image #{image_index}")
        else:
            print(f"❌ Could not extract image URL for Image #{image_index}")

    except Exception as e:
        print(f"❌ Failed to generate Image #{image_index}: {e}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine_id", type=int, default=1)
    parser.add_argument("--total_machines", type=int, default=5)
    args = parser.parse_args()

    all_prompts = read_prompts()
    total_prompts = len(all_prompts)
    
    if total_prompts == 0:
        print("❌ No valid prompts found in prompts.txt!")
        return

    chunk_size = total_prompts // args.total_machines + (1 if total_prompts % args.total_machines != 0 else 0)
    start_idx = (args.machine_id - 1) * chunk_size
    end_idx = min(start_idx + chunk_size, total_prompts)
    
    assigned_prompts = [(i + 1, all_prompts[i]) for i in range(start_idx, end_idx)]
    print(f"🖥️ Machine {args.machine_id} handling {len(assigned_prompts)} image tasks.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Start 30-second background monitor
        monitor_task = asyncio.create_task(live_screenshot_monitor(page, args.machine_id, interval=30))

        for img_num, prompt in assigned_prompts:
            await generate_bing_image(page, prompt, img_num)

        monitor_task.cancel()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
