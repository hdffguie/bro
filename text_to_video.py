import os
import time
from gradio_client import Client

# LTX 2.5 ke official text-to-video backend space ka path
SPACE_NAME = "Lightricks/LTX-2.5" 

def generate_text_to_video():
    output_video = "output_video.mp4"
    
    # 📝 YAHAN APNA PROMPT LIKHEIN (Jaisi video aapko chahiye)
    prompt_text = "A beautiful cinematic wide shot of a futuristic neon city at night, flying cars, rainy cyberpunk atmosphere, 4k resolution."
    negative_prompt_text = "low quality, blurry, worst quality, static, distorted, bad anatomy"

    print("=== GITHUB ACTIONS TEXT-TO-VIDEO RUN SHURU ===")
    print(f"🎬 Your Prompt: '{prompt_text}'")

    # Step 1: Connect to Hugging Face API
    try:
        print(f"🔄 Step 1: Hugging Face space '{SPACE_NAME}' se bina account ke connect ho raha hai...")
        client = Client(SPACE_NAME)
        print("✅ Connection Block: Server se connection successful!")
    except Exception as e:
        print(f"❌ TEST FAILED: Hugging Face space se connect nahi ho paye. Error: {e}")
        return False

    # Step 2: Trigger Video Generation
    try:
        print("🔄 Step 2: LTX 2.5 Model ko request bhej di hai... Processing me thoda samay lag sakta hai...")
        start_time = time.time()
        
        # Hugging Face api call (Text-to-Video parameters ke sath)
        result = client.predict(
            prompt=prompt_text,
            negative_prompt=negative_prompt_text,
            api_name="/predict" # LTX 2.5 ke functional parameters ke hisab se
        )
        
        end_time = time.time()
        print(f"⚡ Server Reply: Model ne processing complete ki! Total Time: {int(end_time - start_time)} seconds.")
        
        # Step 3: Verify Output File
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
        print("💡 Tip: Agar Hugging Face ke server par queue lambi hoti hai to timeout ho jata hai. Kuch der baad 'Re-run job' karein.")
        return False

if __name__ == "__main__":
    success = generate_text_to_video()
    if not success:
        # Isse workflow me red cross (✖) show hoga agar error aayi to
        exit(1) 
