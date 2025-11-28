import os
from pathlib import Path
from google import genai
from PIL import Image
from io import BytesIO


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

# 1. İstemciyi başlatma (Anahtarı doğrudan tırnak içine yazıyoruz)
# NOT: Lütfen önceki uyarımda dediğim gibi bu anahtarı silip YENİSİNİ oluştur.
# Yeni oluşturduğun anahtarı aşağıya yapıştır.
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError("Set GOOGLE_API_KEY as an environment variable or in .env")

client = genai.Client(api_key=api_key) 

try:
    # 2. Resmi bilgisayardan okuma
    print("Resim okunuyor...")
    image = Image.open("mozge.JPG")

    # 3. Prompt (Senin yazdığın karikatür isteği)
    prompt = "Bu görüntüdeki kişinin eğlenceli ve abartılı bir karikatür çizimini yap. Kalın siyah kontur çizgileri ve canlı, düz renkler kullan. Uzay galaksi ve quantum spark temalı, enerjik bir hava ver. Arka plan basit, tek renkli ve temiz olsun."

    print("Yapay zeka çizime başladı (Bu işlem 5-10 saniye sürebilir)...")
    
    # 4. Modele gönderme (Yeni SDK syntax'ı)
    response = client.models.generate_content(
        model="gemini-2.5-flash-image", # Güncel model ismi
        contents=[prompt, image],
        config={
            "response_modalities": ["IMAGE"]
        }
    )

    # 5. Sonucu kaydetme
    if response.candidates[0].content.parts[0].inline_data:
        image_data = response.candidates[0].content.parts[0].inline_data.data
        img_out = Image.open(BytesIO(image_data))
        img_out.save("mozge_karikatur.png")
        print("Harika! Karikatür 'natalie_karikatur.png' olarak kaydedildi.")
    else:
        print("Bir sorun oluştu, resim dönmedi.")

except Exception as e:
    print(f"Hata detayı: {e}")