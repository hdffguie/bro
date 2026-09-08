from playwright.sync_api import sync_playwright
import time
import requests
import os
import argparse
import concurrent.futures
import math
import sys
import re

# Folder setup
SAVE_FOLDER = "bing_automated_images"
os.makedirs(SAVE_FOLDER, exist_ok=True)
PROMPT_FILE = "prompts.txt"

def download_image(url, filename):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # FIX 1: URL parameters ko break nahi kar rahe taaki Bing image server load ho sake
        print(f"📥 Downloading: {url[:60]}...") 
        
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"✅ SAVED: {filename}")
        else:
            print(f"❌ Failed! Status Code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error during download: {e}")

# ==========================================
# WORKER FUNCTION
# ==========================================
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
                time.sleep(4) 
                
                print(f"[Worker {worker_id}] Typing for Image {image_num} | Prompt: {prompt_text[:60]}...")
                
                # Input Box Locator
                search_box = page.get_by_placeholder("Describe the image you want to create")
                if not search_box.is_visible():
                    search_box = page.locator("textarea[name='q'], #sb_form_q, textarea").first
                
                search_box.fill("")
                search_box.fill(prompt_text)
                time.sleep(1)
                
                # Generate Button Locator
                generate_btn = page.locator("button:has-text('Generate'), button:has-text('Create'), #create_btn_div, #create_btn_c").first
                generate_btn.click()
                
                print(f"[Worker {worker_id}] Waiting max 90s for Image {image_num}...")
                
                img_url = None
                
                # FIX 2: Dynamic image detection logic (OIG, tse, th?id= sab accept karega)
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
                        # Exclude icons / logos
                        if "logo" not in src.lower() and "icon" not in src.lower():
                            img_url = src
                            break
                    
                    if img_url:
                        print(f"[Worker {worker_id}] 🎉 Image {image_num} found in {attempt * 2 + 2} seconds!")
                        break 
                
                if img_url:
                    filepath = os.path.join(SAVE_FOLDER, f"Generated_Image_{image_num}.jpg")
                    download_image(img_url, filepath)
                else:
                    print(f"⚠️ [Worker {worker_id}] Image nahi mili Image {image_num} ke liye.")
                    page.screenshot(path=os.path.join(SAVE_FOLDER, f"ERROR_Image_{image_num}.png"))
                    with open(os.path.join(SAVE_FOLDER, "failed_images.txt"), "a") as f:
                        f.write(f"Image {image_num} failed\n")
                    
            except Exception as e:
                print(f"⚠️ Error for Image {image_num}: {e}")
                page.screenshot(path=os.path.join(SAVE_FOLDER, f"CRASH_Image_{image_num}.png"))
            finally:
                browser.close()
                
        time.sleep(3)

# ==========================================
# FILE READING & PARALLEL PROCESSING MATHS
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine_id", type=int, required=True, help="Machine Number (e.g. 1, 2, 3...)")
    parser.add_argument("--total_machines", type=int, default=5, help="Total number of machines running")
    args = parser.parse_args()
    
    machine_id = args.machine_id
    total_machines = args.total_machines
    print(f"🖥️ MACHINE {machine_id} STARTED (Out of {total_machines} machines)!")
    
    if not os.path.exists(PROMPT_FILE):
        print(f"❌ ERROR: {PROMPT_FILE} nahi mila!")
        sys.exit(1)
        
    all_prompts = []
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                # FIX 3: Agar prompt me Pipe (|) hai, toh sirf pehle part ko Image prompt maano
                if "|" in line:
                    line = line.split("|")[0].strip()
                
                clean_line = re.sub(r'^\d+[\.\-\)]?\s*', '', line)
                all_prompts.append(clean_line)
        
    total_prompts = len(all_prompts)
    print(f"📝 Total Prompts Found: {total_prompts}")
    
    if total_prompts == 0:
        print("❌ ERROR: prompts.txt file khali hai!")
        sys.exit(1)

    all_tasks = [(i + 1, all_prompts[i]) for i in range(total_prompts)]
    
    chunk_size = math.ceil(total_prompts / total_machines)
    start_idx = (machine_id - 1) * chunk_size
    end_idx = min(start_idx + chunk_size, total_prompts)
    
    machine_tasks = all_tasks[start_idx:end_idx]
    
    if len(machine_tasks) == 0:
        print(f"⚠️ Machine {machine_id} ke liye koi kaam nahi bacha. Exiting.")
        sys.exit(0)
        
    print(f"⚙️ Machine {machine_id} processing from Image {machine_tasks[0][0]} to {machine_tasks[-1][0]} (Total {len(machine_tasks)} images)")
    
    mid_point = len(machine_tasks) // 2
    worker_1_tasks = machine_tasks[:mid_point]
    worker_2_tasks = machine_tasks[mid_point:]
    
    worker_1_id = (machine_id - 1) * 2 + 1
    worker_2_id = (machine_id - 1) * 2 + 2
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        if worker_1_tasks:
            executor.submit(run_browser_worker, worker_1_id, worker_1_tasks)
        if worker_2_tasks:
            executor.submit(run_browser_worker, worker_2_id, worker_2_tasks)
    
    print(f"✅ MACHINE {machine_id} NE APNA KAAM KHATAM KAR LIYA!")
