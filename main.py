from playwright.sync_api import sync_playwright
import time
import requests
import os
import argparse
import concurrent.futures
import math
import sys
import re

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
SAVE_FOLDER = "bing_automated_images"
os.makedirs(SAVE_FOLDER, exist_ok=True)
PROMPT_FILE = "prompts.txt"

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

def download_image(url, filename):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"✅ SAVED: {filename}")
            return True
        else:
            print(f"❌ Download Failed! Status Code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error during download: {e}")
        return False

def run_browser_worker(worker_id, tasks_list):
    print(f"🤖 Worker {worker_id} started! Processing {len(tasks_list)} images...")
    
    for image_num, prompt_text in tasks_list:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--start-maximized"])
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ) 
            page = context.new_page()
            
            try:
                page.goto("https://www.bing.com/images/create", timeout=60000)
                time.sleep(3) 
                
                print(f"[Worker {worker_id}] Processing Image #{image_num}...")
                
                search_box = page.get_by_placeholder("Describe the image you want to create")
                if not search_box.is_visible():
                    search_box = page.locator("textarea[name='q'], #sb_form_q, textarea, input[type='text']").first
                
                search_box.fill("")
                search_box.fill(prompt_text)
                time.sleep(1)
                
                generate_btn = page.locator("button:has-text('Generate'), button:has-text('Create'), #create_btn_div, #create_btn_c").first
                generate_btn.click()
                
                img_url = None
                for attempt in range(45):
                    time.sleep(2) 
                    all_images = page.evaluate("""() => {
                        const imgs = Array.from(document.querySelectorAll('img'));
                        return imgs.map(img => img.src).filter(src => src && (
                            src.includes('th?id=') || 
                            src.includes('OIG') || 
                            src.includes('bing.net') || 
                            src.includes('tse')
                        ));
                    }""")
                    
                    for src in all_images:
                        if "logo" not in src.lower() and "icon" not in src.lower():
                            img_url = src
                            break
                    
                    if img_url:
                        # Download se thik 5 sec pehle screenshot
                        pre_shot = os.path.join(SAVE_FOLDER, f"pre_download_{image_num}.png")
                        page.screenshot(path=pre_shot)
                        send_telegram_photo(pre_shot, f"📸 Image #{image_num} Ready! Downloading in 5 seconds...")
                        time.sleep(5)
                        break 
                
                # Single download & Telegram push
                if img_url:
                    filepath = os.path.join(SAVE_FOLDER, f"Generated_Image_{image_num}.jpg")
                    if download_image(img_url, filepath):
                        send_telegram_photo(filepath, f"✅ Generated Image #{image_num}")
                else:
                    err_shot = os.path.join(SAVE_FOLDER, f"ERROR_Image_{image_num}.png")
                    page.screenshot(path=err_shot)
                    send_telegram_photo(err_shot, f"❌ Image #{image_num} Generation Failed")
                    
            except Exception as e:
                print(f"⚠️ Error for Image {image_num}: {e}")
            finally:
                browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine_id", type=int, required=True)
    parser.add_argument("--total_machines", type=int, default=5)
    args = parser.parse_args()
    
    if not os.path.exists(PROMPT_FILE):
        sys.exit(1)
        
    all_prompts = []
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                if "|" in line:
                    line = line.split("|")[0].strip()
                clean_line = re.sub(r'^\d+[\.\-\)]?\s*', '', line)
                all_prompts.append(clean_line)
        
    total_prompts = len(all_prompts)
    all_tasks = [(i + 1, all_prompts[i]) for i in range(total_prompts)]
    
    chunk_size = math.ceil(total_prompts / args.total_machines)
    start_idx = (args.machine_id - 1) * chunk_size
    end_idx = min(start_idx + chunk_size, total_prompts)
    
    machine_tasks = all_tasks[start_idx:end_idx]
    if len(machine_tasks) == 0:
        sys.exit(0)
        
    mid_point = math.ceil(len(machine_tasks) / 2)
    worker_1_tasks = machine_tasks[:mid_point]
    worker_2_tasks = machine_tasks[mid_point:]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        if worker_1_tasks:
            executor.submit(run_browser_worker, (args.machine_id - 1) * 2 + 1, worker_1_tasks)
        if worker_2_tasks:
            executor.submit(run_browser_worker, (args.machine_id - 1) * 2 + 2, worker_2_tasks)
