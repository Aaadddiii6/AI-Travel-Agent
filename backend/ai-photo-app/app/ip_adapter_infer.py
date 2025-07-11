from gradio_client import Client, handle_file
from pathlib import Path
import shutil
import os
import traceback

client = Client("multimodalart/Ip-Adapter-FaceID", hf_token=os.getenv("HUGGINGFACE_TOKEN"))

def generate_ai_image(selfie_path: Path, prompt: str) -> list[str]:
    try:
        print("\U0001F4E1 Sending request to Hugging Face...")
        result = client.predict(
            images=[handle_file(str(selfie_path))],
            prompt=prompt,
            negative_prompt="",
            preserve_face_structure=True,
            face_strength=1.3,
            likeness_strength=1.0,
            nfaa_negative_prompt="naked, bikini, skimpy, scanty, bare skin, lingerie, swimsuit, exposed, see-through",
            api_name="/generate_image"
        )

        print("\U0001F4E5 Raw result:")
        from pprint import pprint
        pprint(result)

        # ✅ Process ALL generated images, not just the first one
        if not isinstance(result, list) or len(result) == 0:
            raise ValueError("Unexpected response structure from Hugging Face")

        image_urls = []
        uploads_dir = Path(__file__).parent / "static" / "uploads"
        uploads_dir.mkdir(exist_ok=True)

        for i, item in enumerate(result):
            if isinstance(item, dict) and "image" in item:
                image_path = item["image"]
                if image_path:
                    # Copy each image to static/uploads with unique name
                    dest_filename = f"generated_{i+1}_{os.path.basename(image_path)}"
                    dest_path = uploads_dir / dest_filename
                    shutil.copy(image_path, dest_path)
                    image_urls.append(f"/static/uploads/{dest_filename}")
                    print(f"\U0001F310 Generated image {i+1}: {dest_filename}")

        if not image_urls:
            raise ValueError("No images found in result")

        print(f"\U0001F4F7 Total images generated: {len(image_urls)}")
        return image_urls

    except Exception as e:
        print("\u274C generate_ai_image FAILED:")
        traceback.print_exc()
        raise e
