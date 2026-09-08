import asyncio
import os
import time
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
                res = requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": file}, timeout=15)
                print(f"[Telegram Photo Status]: {res.status_code}")
    except Exception as e:
        print(f"[Telegram Exception]: {e}")

def send_telegram_video(video_path, caption=""):
    """Telegram pe video bhejne ka function"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    try:
        if os.path.exists(video_path):
            with open(video_path, "rb") as file:
                res = requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"video": file}, timeout=120)
                print(f"[Telegram Video Status]: {res.status_code}")
    except Exception as e:
        print(f"[Telegram Exception]: {e}")

async def capture_and_send_status(page, prompt_num, count, step_description=""):
    """Screenshot lekar Telegram pe bhejne ka function"""
    path = "live_status.png"
    try:
        await page.screenshot(path=path)
        caption = f"📸 Prompt #{prompt_num} | Update #{count}: {step_description}"
        send_telegram_photo(path, caption)
    except Exception as e:
        print(f"Screenshot capture failed: {e}")

def load_prompts(filepath="prompt.txt"):
    """prompt.txt file se saare prompts read karne ka function"""
    if not os.path.exists(filepath):
        # Demo file create kar dega agar file na mile
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("A cinematic shot of a futuristic city with flying cars at sunset\n")
            f.write("A cute panda drinking tea in a traditional Japanese garden\n")
        print(f"'{filepath}' file nahi mili thi, ek default file bana di gayi hai.")

    with open(filepath, "r", encoding="utf-8") as f:
        prompts = [line.strip() for line in f.readlines() if line.strip()]
    return prompts

async def process_single_prompt(p, prompt, prompt_num, total_prompts):
    """Ek single prompt ke liye fresh Chrome browser khol kar kaam karne ka function"""
    print(f"\n==========================================")
    print(f"Processing Prompt [{prompt_num}/{total_prompts}]: {prompt}")
    print(f"==========================================")

    # Fresh Chrome Browser Launch
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(accept_downloads=True)
    page = await context.new_page()

    update_count = 1

    try:
        print("Website khol rahe hain...")
        await page.goto("https://upsampler.com/free-video-generator-no-signup", wait_until="networkidle")
        await capture_and_send_status(page, prompt_num, update_count, "Website khul gayi hai")
        update_count += 1

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

        # 3. Prompt text input mein dalna
        prompt_input = page.get_by_placeholder("Enter a prompt to generate a video...")
        await prompt_input.fill(prompt)
        print(f"Prompt add ho gaya: {prompt}")

        # 4. Duration ko 3 seconds se 5 seconds karna
        duration_dropdown = page.get_by_text("3 seconds")
        if await duration_dropdown.is_visible():
            await duration_dropdown.click()
            await asyncio.sleep(1)
            await page.get_by_text("5 seconds", exact=True).click()
            print("Duration 5 seconds set ho gayi.")

        await capture_and_send_status(page, prompt_num, update_count, f"Prompt '{prompt[:30]}...' aur Duration 5s set hai")
        update_count += 1

        # 5. Generate Video button click karna
        generate_btn = page.get_by_role("button", name="Generate Video", exact=True)
        await generate_btn.click()
        print("Video generation start ho chuki hai...")

        # 6. Wait loop: 'See result' button click karna aur video verify karna
        see_result_btn = page.locator("button:has-text('See result'), a:has-text('See result')").first
        video_element = page.locator("video:not([src*='_static'])").first

        start_time = time.time()
        max_wait_seconds = 300  # 5 Minute max wait
        video_ready = False

        while time.time() - start_time < max_wait_seconds:
            await asyncio.sleep(10)  # Har 10 sec mein update

            # Check agar 'See result' button dikh gaya ho
            if await see_result_btn.is_visible():
                print("'See result' button mil gaya! Click kar rahe hain...")
                await capture_and_send_status(page, prompt_num, update_count, "Result Ready! 'See result' click kar rahe hain...")
                update_count += 1
                await see_result_btn.click()
                await asyncio.sleep(3)

            # Check if video is visible
            if await video_element.count() > 0 and await video_element.is_visible():
                print("Video generate ho gayi hai!")
                await capture_and_send_status(page, prompt_num, update_count, "Video screen par show ho gayi hai!")
                update_count += 1
                video_ready = True
                break
            else:
                await capture_and_send_status(page, prompt_num, update_count, "Video process ho rahi hai...")
                update_count += 1

        if not video_ready:
            raise Exception("Video generation time limit exceed ho gayi (5 mins).")

        # 7. Video download karna aur Telegram par bhejna
        video_filename = f"video_prompt_{prompt_num}.mp4"
        video_src = await video_element.get_attribute("src")

        if video_src:
            download_btn = page.locator("a:has-text('Download'), button:has-text('Download')").first
            if await download_btn.is_visible():
                async with page.expect_download() as download_info:
                    await download_btn.click()
                download = await download_info.value
                await download.save_as(video_filename)
            else:
                video_data = requests.get(video_src).content
                with open(video_filename, "wb") as f:
                    f.write(video_data)

            print(f"Video {video_filename} download ho gayi!")
            send_telegram_video(video_filename, f"✅ Video #{prompt_num} Ready!\n\n📌 Prompt: {prompt}")

    except Exception as e:
        print(f"Error aaya Prompt #{prompt_num} par: {e}")
        error_img = f"error_prompt_{prompt_num}.png"
        await page.screenshot(path=error_img)
        send_telegram_photo(error_img, f"❌ Error on Prompt #{prompt_num}: {e}")

    finally:
        # Browser completely delete/close karna
        print("Chrome delete/close kar rahe hain...")
        await browser.close()

async def main():
    prompts = load_prompts("prompt.txt")
    total = len(prompts)
    print(f"Total {total} prompts mile hain.")

    async with async_playwright() as p:
        for idx, prompt in enumerate(prompts, start=1):
            await process_single_prompt(p, prompt, idx, total)
            
            # Har video ke baad 2 second ruk kar fresh chrome start karne ke liye
            if idx < total:
                print("2 second wait karke next fresh Chrome instance start kar rahe hain...")
                await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
