import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from py_yt import VideosSearch
# Make sure YOUTUBE_IMG_URL is defined in your config
from config import YOUTUBE_IMG_URL 

def truncate(text, max_len=30):
    """Truncates text to fit within the card."""
    return text if len(text) < max_len else text[:max_len] + "..."

def make_rounded_corners(img, radius=30):
    """Crops an image to have rounded corners."""
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    output = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
    output.putalpha(mask)
    return output

def draw_aesthetic_controls(draw, x, y):
    """
    Draws aesthetic Play/Pause/Skip buttons directly on the canvas.
    Centered at (x, y).
    """
    fill_color = "#FFFFFF" # White icons

    # 1. Play/Pause Button (Center) - Representing "Now Playing"
    # Draw two vertical bars for Pause
    bar_width = 10
    bar_height = 35
    gap = 8

    # Left Bar
    draw.rounded_rectangle(
        (x - (bar_width + gap//2), y - bar_height//2, x - gap//2, y + bar_height//2), 
        radius=4, fill=fill_color
    )
    # Right Bar
    draw.rounded_rectangle(
        (x + gap//2, y - bar_height//2, x + (bar_width + gap//2), y + bar_height//2), 
        radius=4, fill=fill_color
    )

    # 2. Previous Button (Left)
    prev_x = x - 90
    size = 22
    # Arrow pointing left
    draw.polygon(
        [(prev_x + size//2, y - size//2), (prev_x + size//2, y + size//2), (prev_x - size//2, y)], 
        fill=fill_color
    )
    # Vertical Bar
    draw.rounded_rectangle(
        (prev_x - size//2 - 6, y - size//2, prev_x - size//2 - 2, y + size//2), 
        radius=2, fill=fill_color
    )

    # 3. Next Button (Right)
    next_x = x + 90
    # Arrow pointing right
    draw.polygon(
        [(next_x - size//2, y - size//2), (next_x - size//2, y + size//2), (next_x + size//2, y)], 
        fill=fill_color
    )
    # Vertical Bar
    draw.rounded_rectangle(
        (next_x + size//2 + 2, y - size//2, next_x + size//2 + 6, y + size//2), 
        radius=2, fill=fill_color
    )

async def gen_thumb(videoid: str, thumb_size=(1280, 720)):
    path = f"cache/{videoid}.png"
    if os.path.isfile(path):
        return path
    try:
        # --- Fetch Data ---
        url = f"https://www.youtube.com/watch?v={videoid}"
        results = VideosSearch(url, limit=1, with_live=False)
        data = (await results.next())["result"][0]

        title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        duration = data.get("duration") or "Live"
        channel = data.get("channel", {}).get("name", "Unknown Artist")
        if isinstance(channel, dict): channel = channel.get("name", "Unknown Artist")

        thumb_url = data["thumbnails"][0]["url"].split("?")[0]

        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url) as resp:
                content = await resp.read()

        temp_path = f"cache/thumb_{videoid}.png"
        async with aiofiles.open(temp_path, "wb") as f:
            await f.write(content)

        # --- Image Processing ---
        try:
            # Adjust font sizes to match the look
            font_title = ImageFont.truetype("AviaxMusic/assets/font3.ttf", 35)
            font_artist = ImageFont.truetype("AviaxMusic/assets/font3.ttf", 28)
            font_sub = ImageFont.truetype("AviaxMusic/assets/font2.ttf", 22) # "Now Playing"
            font_time = ImageFont.truetype("AviaxMusic/assets/font2.ttf", 20)
        except OSError:
            font_title = ImageFont.truetype("arial.ttf", 35)
            font_artist = ImageFont.truetype("arial.ttf", 28)
            font_sub = ImageFont.truetype("arial.ttf", 22)
            font_time = ImageFont.truetype("arial.ttf", 20)

        base_img = Image.open(temp_path).convert("RGBA")

        # 1. Background
        bg = base_img.resize(thumb_size, Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=30))

        # Overlay: Light Black / Dark Grey tint
        # (20, 20, 20) is a very dark grey, 200 alpha allows some blur to show
        overlay = Image.new("RGBA", thumb_size, (20, 20, 20, 200)) 
        bg = Image.alpha_composite(bg, overlay)
        draw = ImageDraw.Draw(bg)

        # 2. Main Player Card
        center_x, center_y = thumb_size[0] // 2, thumb_size[1] // 2
        card_w, card_h = 650, 670 # Increased height for better spacing
        card_x1 = center_x - card_w // 2
        card_y1 = center_y - card_h // 2

        # Card Background: "Light Black" (Matte Dark Grey)
        draw.rounded_rectangle(
            (card_x1, card_y1, card_x1 + card_w, card_y1 + card_h), 
            radius=40, fill="#202020" 
        )

        # 3. Album Art with Golden Border
        art_w, art_h = 580, 320 
        art = base_img.convert("RGBA")
        art = ImageOps.fit(art, (art_w, art_h), centering=(0.5, 0.5))
        art = make_rounded_corners(art, radius=30)

        art_y = card_y1 + 30
        art_x = center_x - art_w // 2

        # Gold Border
        border_color = "#FFD700" 
        border_width = 5
        draw.rounded_rectangle(
            (art_x - border_width, art_y - border_width, 
             art_x + art_w + border_width, art_y + art_h + border_width),
            radius=35, fill=None, outline=border_color, width=border_width
        )
        bg.paste(art, (art_x, art_y), art)

        # 4. Text Information
        # Layout: Art -> "Now Playing" -> Title -> Channel -> Bar -> Controls
        current_y = art_y + art_h + 30

        # "Now Playing"
        draw.text((center_x, current_y), "Now Playing", font=font_sub, fill="#888888", anchor="mm")
        current_y += 40

        # Title
        clean_title = truncate(title, 25)
        draw.text((center_x, current_y), clean_title, font=font_title, fill="white", anchor="mm")
        current_y += 40

        # Channel
        clean_channel = truncate(channel, 30)
        draw.text((center_x, current_y), clean_channel, font=font_artist, fill="#bbbbbb", anchor="mm")
        current_y += 50

        # 5. Progress Bar
        bar_width = 520
        bar_h = 6
        bar_start_x = center_x - bar_width // 2

        # Background Line
        draw.line(
            (bar_start_x, current_y, bar_start_x + bar_width, current_y), 
            fill="#444444", width=bar_h
        )
        # Active Line
        progress_len = int(bar_width * 0.35) 
        draw.line(
            (bar_start_x, current_y, bar_start_x + progress_len, current_y), 
            fill="white", width=bar_h
        )
        # Knob
        draw.ellipse(
            (bar_start_x + progress_len - 8, current_y - 8, 
             bar_start_x + progress_len + 8, current_y + 8), 
            fill="white"
        )

        # Timestamps
        time_y = current_y + 25
        draw.text((bar_start_x, time_y), "1:24", font=font_time, fill="#888888", anchor="lm")
        draw.text((bar_start_x + bar_width, time_y), duration, font=font_time, fill="#888888", anchor="rm")

        # 6. Controls
        ctrl_y = time_y + 50
        draw_aesthetic_controls(draw, center_x, ctrl_y)

        # --- Save ---
        bg.save(path)
        os.remove(temp_path)
        return path

    except Exception as ex:
        print(f"Error generating thumbnail: {ex}")
        return YOUTUBE_IMG_URL