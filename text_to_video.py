import os
import time
from gradio_client import Client

# LTX 2.5 ke backend space ka path
SPACE_NAME = "Lightricks/LTX-2.5" 

def generate_text_to_video():
    output_video = "output_video.mp4"
    prompt_file = "prompt.txt"
    negative_prompt_text = "low quality, blurry, worst quality, static, distorted, bad anatomy"

    print("=== GITHUB ACTIONS TEXT-TO-VIDEO RUN SHURU ===")

    # Step 1: Prompt file check karna
    if not os.path.exists(prompt_file):
        print(f"❌ TEST FAILED: Repository me '{prompt_file}' nahi mili.")
        print("💡 Solution: Pehle prompt.txt file banayein aur usme apna text likhein.")
        return False

    with open(prompt_file, "r") as f:
        prompt_text = f.read().strip()

    if not prompt_text:
        print("❌ TEST FAILED: prompt.txt file khali hai! Kripya usme kuch likhein.")
        return False

    print(f"🎬 Loaded Prompt from file: '{prompt_text}'")

    # Step 2: Connect to Hugging Face API
    try:
        print(f"🔄 Step 2: Hugging Face space '{SPACE_NAME}' se bina account ke connect ho raha hai...")
        client = Client(SPACE_NAME)
        print("✅ Connection Block: Server se connection successful!")
    except Exception as e:
        print(f"❌ TEST FAILED: Hugging Face space se connect nahi ho paye. Error: {e}")
        return False

    # Step 3: Trigger Video Generation (FIXED BY PASSING POSITIONAL ARGUMENTS)
    try:
        print("🔄 Step 3: LTX 2.5 Model ko request bhej di hai... Processing chal rahi hai...")
        start_time = time.time()
        
        # FIXED: Keyword hata kar positional arguments pass kiye hain.
        # Order: 1st argument=prompt, 2nd argument=negative_prompt
        result = client.predict(
            prompt_text,
            negative_prompt_text,
            fn_index=0
        )
        
        end_time = time.time()
        print(f"⚡ Server Reply: Model ne processing complete ki! Total Time: {int(end_time - start_time)} seconds.")
        
        # Step 4: Verify Output File
        if result and os.path.exists(result):
            os.rename(result, output_video)
            file_size = os.path.getsize(output_video) / (1024 * 1024) # MB me size
            
            print("\n==============================================")
            print("🎉 🎉 SUCCESS: TEXT TO VIDEO WORKING! 🎉 🎉")
            print(f"📁 Video Location: {output_video}")
            print(f"💾 Video Size: {file_size:.2f} MB")
            print("==============================================")
            return True
        else:
            print("❌ TEST FAILED: Server se output video file generate nahi hui.")
            return False
            
    except Exception as e:
        print("\n❌ TEST FAILED: Processing ke dauran error aayi.")
        print(f"📝 Error Details: {e}")
        print("💡 Tip: Agar server par zyada traffic hai to thodi der baad fir se 'Re-run job' karein.")
        return False

if __name__ == "__main__":
    success = generate_text_to_video()
    if not success:
        exit(1) 
