from PIL import Image, ImageDraw, ImageFont
import io
import base64

def resize_image(image_bytes, max_width=1024):
    """Resizes an image to a maximum width while maintaining aspect ratio."""
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    if w > max_width:
        ratio = max_width / w
        new_size = (int(w * ratio), int(h * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=80)
    return output.getvalue()

def add_grid(image_bytes):
    """Adds a 10x10 numbered grid to the image to help the LLM with coordinates."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    # Try to load a larger font, fallback to default
    try:
        # On Windows, arial.ttf is usually present
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    # Draw grid lines and numbers
    for i in range(11):
        x = (i * w) // 10
        y = (i * h) // 10
        
        # Vertical lines
        draw.line([(x, 0), (x, h)], fill="red", width=1)
        # Horizontal lines
        draw.line([(0, y), (w, y)], fill="red", width=1)
        
        # Add coordinate numbers with a shadow/outline for readability
        if i < 10:
            text = str(i * 100)
            for offset in [(1,1), (-1,-1), (1,-1), (-1,1)]:
                draw.text((x + 2 + offset[0], 2 + offset[1]), text, fill="black", font=font)
                draw.text((2 + offset[0], y + 2 + offset[1]), text, fill="black", font=font)
            draw.text((x + 2, 2), text, fill="red", font=font)
            draw.text((2, y + 2), text, fill="red", font=font)

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=80)
    return output.getvalue()

def mark_click(image_bytes, x_pct, y_pct):
    """Draws a green dot at the specified 0-1000 coordinate for debugging."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    x = (x_pct * w) // 1000
    y = (y_pct * h) // 1000
    
    radius = 10
    draw.ellipse([(x - radius, y - radius), (x + radius, y + radius)], fill="lime", outline="black")
    
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=80)
    return output.getvalue()

SYSTEM_PROMPT = """
You are a web agent that navigates the web using screenshots. 
You will receive a screenshot with a RED GRID overlay (numbered 0-1000).
Your goal is to complete the user's task.

ACTIONS:
1. click(x, y): Click at coordinates (0-1000).
2. type(text, x, y): Click at (x, y) and type text.
3. paste(text, x, y): Click at (x, y) and PASTE text (faster for long strings).
4. scroll(direction): 'up' or 'down'.
5. wait(): Wait 2s.
6. finish(): Task is complete.
7. ask_user(reason): Pause for user input.

PRECISION RULES:
- Use the RED GRID to estimate exact coordinates.
- Before clicking, carefully look at the numbers on the grid.
- Return multiple actions in a list if you are confident.

JSON FORMAT:
{
  "thought": "Describe what you see and the coordinates you calculated",
  "actions": [{"action": "click", "params": [450, 210]}]
}
"""
