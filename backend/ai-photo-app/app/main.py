from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
from .ip_adapter_infer import generate_ai_image


app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Static and template setup
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "output_images": None})

@app.post("/", response_class=HTMLResponse)
async def handle_form(
    request: Request,
    selfie: UploadFile = File(...),
    prompt: str = Form(...)
):
    try:
        filename = selfie.filename or "uploaded.jpg"
        upload_path = UPLOAD_DIR / filename

        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(selfie.file, buffer)

        print("📤 Saved selfie at:", upload_path)

        # 🔥 Generate using IP-Adapter (now returns a list of images)
        image_urls = generate_ai_image(upload_path, prompt)
        print("✅ Generated image URLs:", image_urls)

        return templates.TemplateResponse("index.html", {
            "request": request,
            "output_images": image_urls,
            "prompt": prompt
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "output_images": None,
            "prompt": prompt,
            "error": str(e)
        })
