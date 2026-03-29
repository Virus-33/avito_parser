import requests
from PIL import Image
from io import BytesIO


def to_jpg(img: Image):
    img_rgb: Image = img.convert('RGB')
    jpg_bytes = BytesIO()
    img_rgb.save(jpg_bytes, format='JPEG', quality=85)
    jpg_bytes.seek(0)
    return jpg_bytes


def get_image(url):
    resp = requests.get(url)
    resp.raise_for_status()

    return Image.open(BytesIO(resp.content))


def get_jpeg(url):
    img = get_image(url)
    return to_jpg(img)
