import os
from PIL import Image, ImageChops
import pywikibot
from datetime import datetime

def log_debug(message, debug_path):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    os.makedirs(os.path.dirname(debug_path), exist_ok=True)
    with open(debug_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\n")

def composite_images(base_path, overlay_path):
    """
    Lay overlay image on top of base image and return the result.
    """
    base = Image.open(base_path).convert("RGBA")
    overlay = Image.open(overlay_path).convert("RGBA")
    result = Image.alpha_composite(base, overlay)
    return result

def crop_whitespace(image):
    """
    Crop all transparent/white space from the image.
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    bg = Image.new("RGBA", image.size, (255, 255, 255, 0))
    diff = ImageChops.difference(image, bg)
    bbox = diff.getbbox()
    if bbox:
        return image.crop(bbox)
    return image

def scale_image_to_min_size(image, min_size=500):
    """
    Scale image proportionally so that at least one side is >= min_size.
    """
    width, height = image.size
    scale = max(min_size / width, min_size / height)
    new_size = (int(width * scale), int(height * scale))
    return image.resize(new_size, Image.NEAREST)

def upload_image(image, filename, caption_text=None, categories=None, debug_path="debug.log", upload_comment="Image upload"):
    """
    Save, upload to wiki, and apply caption/licensing/categories.
    """
    temp_path = os.path.join("temp_upload", filename)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    image.save(temp_path)

    site = pywikibot.Site()
    file_page = pywikibot.FilePage(site, f"File:{filename}")

    wiki_text = []
    if caption_text:
        wiki_text.append("==Caption==")
        wiki_text.append(caption_text)
        wiki_text.append("")

    wiki_text.append("==Licensing==")
    wiki_text.append("{{License|game}}")

    for cat in categories or []:
        wiki_text.append(f"[[Category:{cat}]]")

    file_page.text = "\n".join(wiki_text)

    try:
        if file_page.exists():
            log_debug(f"Skipped upload for {filename} (already exists on wiki)", debug_path)
        else:
            file_page.upload(temp_path, comment=upload_comment, ignore_warnings=False)
            log_debug(f"Uploaded: {filename}", debug_path)
    except Exception as e:
        log_debug(f"Upload failed for {filename}: {e}", debug_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
