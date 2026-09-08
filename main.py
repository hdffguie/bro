import asyncio
import os
import argparse
from playwright.async_api import async_playwright

IMAGE_DIR = "bing_automated_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

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

async def generate_bing_image(page, prompt, image_index):
    print(f"🎨 Generating Image #{image_index}: {prompt[:50]}...")
    await page.goto("https://www.bing.com/images/create", wait_until="networkidle")
    
    # Fill Prompt
    textarea = page.locator("#sb_form_q")
    await textarea.fill(prompt)
    
    # Click Create
    create_btn = page.locator("#create_btn_div")
    await create_btn.click()
    
    try:
        await page.wait_for_selector(".mimg", timeout=120000)
        await asyncio.sleep(5)
        
        first_img = page.locator(".mimg").first
        await first_img.click()
        await asyncio.sleep(3)
        
        img_element = page.locator("img.mainImage").first
        img_url = await img_element.get_attribute("src")
        
        if img_url:
            response = await page.request.get(img_url)
            img_bytes = await response.body()
            img_path = os.path.join(IMAGE_DIR, f"Generated_Image_{image_index}.jpg")
            with open(img_path, "wb") as f:
                f.write(img_bytes)
            print(f"✅ Image #{image_index} Saved successfully.")
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
        context = await browser.new_context()
        page = await context.new_page()

        for img_num, prompt in assigned_prompts:
            await generate_bing_image(page, prompt, img_num)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
