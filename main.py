from playwright.sync_api import sync_playwright
import sys

def main():
    # Playwright start karna
    with sync_playwright() as p:
        # GitHub actions mein headless True rakhna zaroori hai
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Video banne mein time lagta hai, isliye timeout 5 minutes (300,000 ms) kar diya hai
        page.set_default_timeout(300000)

        try:
            print("Website open kar rahe hain...")
            page.goto('https://upsampler.com/free-video-generator-no-signup')

            # 1. Prompt likhna
            print("Prompt enter kar rahe hain...")
            page.fill('textarea[placeholder*="Enter a prompt"]', 'A cinematic drone shot of a futuristic city at sunset, 4k resolution')

            # 2. Duration 3s se 5s karna
            print("Duration change kar rahe hain...")
            page.click('text="3 seconds"') 
            page.wait_for_timeout(500) # Dropdown open hone ke liye thoda wait
            page.click('text="5 seconds"')

            # 3. Generate Video par click karna
            print("Generate Video par click kar rahe hain...")
            page.click('button:has-text("Generate Video")')

            # 4. Video generate hone ka wait karna
            print("Video generate hone ka wait kar rahe hain (Isme time lag sakta hai)...")
            # Yahan hum assume kar rahe hain ki banne ke baad Download ka button aayega
            page.wait_for_selector('button:has-text("Download")')

            # 5. Video download karna
            print("Video download kar rahe hain...")
            # Python Playwright mein download handle karne ka tarika:
            with page.expect_download() as download_info:
                page.click('button:has-text("Download")')
            
            download = download_info.value
            download.save_as('./generated_video.mp4')
            print("Video successfully download ho gayi!")

        except Exception as e:
            print(f"Koi error aayi hai: {e}")
            
            # Error aane par screenshot lena
            page.screenshot(path="error_screenshot.png", full_page=True)
            print("Error ka screenshot 'error_screenshot.png' ke naam se save ho gaya hai.")
            
            # GitHub Action ko fail karne ke liye error code ke sath exit karna
            sys.exit(1)
            
        finally:
            browser.close()

if __name__ == "__main__":
    main()
