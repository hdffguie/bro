import os
import time
from gradio_client import Client

# LTX 2.5 ke backend space ka path (Aap ise gokaygokay/LTX-2.5 se bhi badal sakte hain)
SPACE_NAME = "Lightricks/LTX-2.5" 

def generate_text_to_video():
    output_video = "output_video.mp4"
    prompt_file = "prompt.txt"
    negative_prompt_text = "low quality, blurry, worst quality, static, distorted, bad anatomy"

    print("=== GITHUB ACTIONS TEXT-TO-VIDEO RUN SHURU ===")

    # Step 1: Prompt file check karna
    if not os.path.exists(prompt_file):
        print(f"❌ TEST FAILED: Repository me '{prompt_file}' nahi mili.")
        return False

    with open(prompt_file, "r") as f:
        prompt_text = f.read().strip()

    if not prompt_text:
        print("❌ TEST FAILED: prompt.txt file khali hai!")
        return False

    print(f"🎬 Loaded Prompt: '{prompt_text}'")

    # Step 2: Connect to Hugging Face
    try:
        print(f"🔄 Step 2: Hugging Face space '{SPACE_NAME}' se connect ho raha hai...")
        client = Client(SPACE_NAME)
        print("✅ Connection Block: Server se connection successful!")
    except Exception as e:
        print(f"❌ TEST FAILED: Connection error: {e}")
        return False

    # Step 3: Trigger Video Generation with Smart Retry Loop
    max_retries = 3
    retry_delay = 5 # seconds

    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔄 Step 3 (Attempt {attempt}/{max_retries}): Request bhej di hai, processing chal rahi hai...")
            start_time = time.time()
            
            # Positional arguments ke sath prediction
            result = client.predict(
                prompt_text,
                negative_prompt_text,
                fn_index=0
            )
            
            end_time = time.time()
            print(f"⚡ Server Reply: Success! Total Time: {int(end_time - start_time)} seconds.")
            
            # Step 4: Verify File
            if result and os.path.exists(result):
                os.rename(result, output_video)
                file_size = os.path.getsize(output_video) / (1024 * 1024)
                print("\n==============================================")
                print("🎉 🎉 SUCCESS: TEXT TO VIDEO WORKING! 🎉 🎉")
                print(f"💾 Video Size: {file_size:.2f} MB")
                print("==============================================")
                return True
                
        except Exception as e:
            print(f"⚠️ Attempt {attempt} me dikkat aayi: Server Busy ya Upstream Error.")
            if attempt < max_retries:
                print(f"⏳ {retry_delay} seconds ruk kar fir se koshish kar rahe hain...")
                time.sleep(retry_delay)
            else:
                print("\n❌ ALL ATTEMPTS FAILED: Hugging Face ka yeh server abhi heavy load par hai.")
                print("💡 Solution: Code me line 6 par SPACE_NAME ko 'gokaygokay/LTX-2.5' kar dein, ya thodi der baad Re-run karein.")
                return False

if __name__ == "__main__":
    success = generate_text_to_video()
    if not success:
        exit(1)
