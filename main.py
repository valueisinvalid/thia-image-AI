import asyncio
import os
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from google import genai
from PIL import Image, UnidentifiedImageError


def _load_env_file(path: str = ".env") -> None:
    """Populate os.environ from a simple KEY=VALUE .env file if it exists."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError("Set GOOGLE_API_KEY as an environment variable or in .env")

client = genai.Client(api_key=api_key)

app = FastAPI(
    title="Karikatür Üretici API",
    description="Gemini tabanlı karikatür üretim servisi",
    version="1.0.0",
)

DEFAULT_PROMPT = (
    "Bu görüntüdeki kişinin eğlenceli ve abartılı bir karikatür çizimini yap. "
    "Kalın siyah kontur çizgileri ve canlı, düz renkler kullan. Uzay galaksi "
    "ve quantum spark temalı, enerjik bir hava ver. Arka plan basit, tek renkli "
    "ve temiz olsun."
)


def _generate_caricature(image_bytes: bytes, prompt: str) -> BytesIO:
    """Blocking helper that sends the request to Gemini and returns image bytes."""
    try:
        pil_image = Image.open(BytesIO(image_bytes))
    except UnidentifiedImageError as exc:
        raise ValueError("Geçerli bir görüntü dosyası yükleyin.") from exc

    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[prompt, pil_image],
        config={"response_modalities": ["IMAGE"]},
    )

    inline_data = response.candidates[0].content.parts[0].inline_data
    if not inline_data:
        raise RuntimeError("Model görüntü üretmedi, lütfen tekrar deneyin.")

    output_io = BytesIO(inline_data.data)
    output_io.seek(0)
    return output_io


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "message": "Karikatür servisi hazır."}


@app.post("/caricature")
async def create_caricature(
    image: UploadFile = File(..., description="Karikatürü yapılacak görüntü"),
    prompt: str = Form(DEFAULT_PROMPT),
):
    file_bytes = await image.read()
    loop = asyncio.get_running_loop()

    try:
        caricature_io = await loop.run_in_executor(
            None, _generate_caricature, file_bytes, prompt
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected errors
        raise HTTPException(status_code=500, detail="Bilinmeyen bir hata oluştu.") from exc

    filename = Path(image.filename or "karikatur").stem + "_caricature.png"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(caricature_io, media_type="image/png", headers=headers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)