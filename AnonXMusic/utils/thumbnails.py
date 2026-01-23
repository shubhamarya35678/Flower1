import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from py_yt import VideosSearch

from config import YOUTUBE_IMG_URL

def truncate(text, max_len=30):
    words = text.split()
    lines = ["", ""]
    i = 0
    for word in words:
        if len(lines[i]) + len(word) + 1 <= max_len:
            lines[i] += (" " if lines[i] else "") + word
        elif i == 0:
            i = 1
    return lines

def get_rounded_square(img, size, radius):
    # Crop the image to a square first (center crop)
    w, h = img.size
    min_dim = min(w, h)
    left = (w - min_dim) / 2
    top = (h - min_dim) / 2
    right = (w + min_dim) / 2
    bottom = (h + min_dim) / 2
    img = img.crop((left, top, right, bottom))

    # Resize to target size
    img = img.resize((size, size), Image.Resampling.LANCZOS)

    # Create rounded mask
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)

    # Apply mask
    output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    output.paste(img, (0, 0), mask)
    return output

async def gen_thumb(videoid: str, thumb_size=(1280, 720)):
    path = f"cache/{videoid}.png"
    if os.path.isfile(path):
        return path
    try:
        url = f"https://www.youtube.com/watch?v={videoid}"
        results = VideosSearch(url, limit=1, with_live=False)
        data = (await results.next())["result"][0]

        title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        duration = data.get("duration") or "00:00"
        views = data.get("viewCount", {}).get("short", "Unknown Views")
        channel = data.get("channel", {}).get("name", "Unknown Channel")
        thumb_url = data["thumbnails"][0]["url"].split("?")[0]

        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url) as resp:
                content = await resp.read()

        temp_path = f"cache/thumb_{videoid}.png"
        async with aiofiles.open(temp_path, "wb") as f:
            await f.write(content)

        # Open image
        base_img = Image.open(temp_path).convert("RGBA")

        # --- 1. Background Generation (Light Blur) ---
        bg = base_img.copy()
        bg = bg.resize(thumb_size, Image.Resampling.LANCZOS)
        # Apply Gaussian Blur for a smoother "light blur" look
        bg = bg.filter(ImageFilter.GaussianBlur(radius=15))
        # Add a slight dark overlay so white text is readable
        overlay = Image.new("RGBA", thumb_size, (0, 0, 0, 100))
        bg = Image.alpha_composite(bg, overlay)

        # --- 2. Square Thumbnail Generation ---
        # Create a rounded square thumbnail
        square_thumb = get_rounded_square(base_img, size=450, radius=40)
        # Paste slightly to the left
        bg.paste(square_thumb, (100, 135), square_thumb)

        # --- 3. Text Drawing ---
        draw = ImageDraw.Draw(bg)

        # Define Fonts (Adjust sizes to match reference)
        # Assuming font2 is a regular font and font3 is bold/display
        font_header = ImageFont.truetype("AviaxMusic/assets/font3.ttf", 45) # NOW PLAYING
        font_title = ImageFont.truetype("AviaxMusic/assets/font3.ttf", 55)  # Song Name
        font_meta = ImageFont.truetype("AviaxMusic/assets/font2.ttf", 40)   # Details

        # Text Positions (Right side of the image)
        x_start = 600
        y_pos = 140

        # "NOW PLAYING" Header
        draw.text((x_start, y_pos), "NOW PLAYING", font=font_header, fill="white")

        # Title (Truncated if too long)
        y_pos += 80 
        t1, t2 = truncate(title, max_len=25)
        draw.text((x_start, y_pos), t1, font=font_title, fill="white")
        if t2:
            y_pos += 60
            draw.text((x_start, y_pos), t2, font=font_title, fill="white")

        # Metadata Lines (Separated as requested)
        y_pos += 80

        # Views
        draw.text((x_start, y_pos), f"Views : {views} views", font=font_meta, fill="white")

        # Duration
        y_pos += 60
        draw.text((x_start, y_pos), f"Duration : {duration} Mins", font=font_meta, fill="white")

        # Channel
        y_pos += 60
        draw.text((x_start, y_pos), f"Channel : {channel}", font=font_meta, fill="white")

        # Save result
        bg.save(path)
        os.remove(temp_path)
        return path

    except Exception as ex:
        print(ex)
        return YOUTUBE_IMG_URL