import os
import random
import requests
import zipfile
import json
import smtplib
from email.message import EmailMessage
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont

# --- Settings (read from env; NEVER hardcode secrets) ---
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
ZIP_FILE = os.getenv("ZIP_FILE", "output_package.zip")
NUM_RECOMMENDATIONS = int(os.getenv("NUM_RECOMMENDATIONS", "5"))

# Secrets (add them as GitHub Secrets; see steps below)
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", EMAIL_SENDER)

# Font: prefer provided FONT_PATH, else use DejaVu (present on ubuntu-latest after apt install)
FONT_PATH = os.getenv("FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

TIKTOK_TITLES = [
    "This manga ruined my sleep ;)", "Better than most anime tbh", "Why is no one talking about this??",
    "If you like villainess, READ THIS", "You’ll thank me later :)"
]
TAGS = "#manga #manhwa #anime #romanceanime #romancemanga #isekai #animeedit #otaku #mangarecommendation #trending"

MANGA_LIST = [
    ("Operation: True Love", "Romance about first love struggles, surprisingly deep."),
    ("See You in My 19th Life", "Reincarnation romance across lifetimes."),
    ("Marry My Husband", "Revenge rebirth romance drama."),
    ("What's Wrong with Secretary Kim?", "Office rom-com with iconic couple."),
    ("Under the Oak Tree", "Knight x noblewoman arranged marriage romance."),
    ("A Business Proposal", "Fake-date CEO romance, sweet & funny."),
    ("The Remarried Empress", "Strong female lead navigating betrayal and new love."),
    ("Light and Shadow", "Servant becomes duchess; romance & politics."),
    ("Doctor Elise", "Reincarnated noblewoman becomes surgeon princess."),
    ("Adelaide", "Noblewoman embraces her chaotic second chance."),
    ("This Girl is a Little Wild", "Ex-warrior reincarnates as noble girl, chaotic romance."),
    ("Ojousama no Untenshu", "Period romance with sweet chauffeur love."),
    ("Ojousama no Mission", "Strong-willed lady defies expectations in love."),
    ("Ojousama no Untenshu Returns", "Follow-up with more mature struggles."),
    ("Ojousama no Yubi", "Another elegant old-school romance gem."),
    ("Ojousama no Untenshu (Side Stories)", "Short romance arcs worth hunting."),
    ("Ojousama no Untenshu Season 2", "Continuation with deeper drama."),
    ("Ojousama no Mission Returns", "Gentle, lesser-known emotional work."),
    ("Ojousama no Untenshu Reborn", "Reboot with modern artstyle."),
    ("Ojousama no Koi", "Nostalgic style romance, underrated."),
    ("Ojousama no Ai", "Pure romance with tender storytelling."),
    ("Ojousama no Smile", "Untranslated but known hidden jewel."),
    ("Ojousama no Tears", "Emotional story blending romance and tragedy."),
    ("Orange", "A letter from the future warns her to save her classmate."),
    ("Ao Haru Ride", "First love rekindled with bittersweet teen drama."),
    ("Strobe Edge", "Quiet girl’s first romance: realistic and touching."),
    ("Toradora!", "Fiery girl, quiet boy, surprising partnership turns to love."),
    ("Honey and Clover", "College romance with unrequited love and messy hearts."),
    ("Boys Over Flowers", "Classic rich-boy x poor-girl love drama."),
    ("Daytime Shooting Star", "Small-town girl moves to Tokyo, tangled romances."),
    ("Say I Love You", "Socially awkward girl learns to open up."),
    ("We Were There", "Bittersweet romance with love, loss, and healing."),
    ("Good Morning Call", "Living together rom-com between students."),
    ("My Dress-Up Darling", "Cosplay + romance = heart-thumping sweetness."),
    ("Takane to Hana", "Comedy romance with cheeky rich guy and ordinary girl."),
    ("Kimi wa Pet", "Quirky adult romance: woman adopts man as her pet."),
    ("Nodame Cantabile", "Music-driven romance with eccentric pianist."),
    ("Perfect World", "A love story facing disability and harsh reality."),
    ("Mushoku Tensei", "Jobless man reincarnates with a second chance at life."),
    ("Re:Zero", "Boy stuck in death-loop, romance and despair in another world."),
    ("That Time I Got Reincarnated as a Slime", "Slime OP powers + kingdom building."),
    ("Konosuba", "Comedy isekai with useless goddess and chaotic party."),
    ("Jobless Oblige", "Underrated isekai manhwa with noble politics."),
    ("The Beginning After the End", "Reborn king in fantasy world seeks peace and family."),
    ("Solo Leveling", "Weak hunter becomes strongest. Action, cool factor 100%."),
    ("Leveling With the Gods", "Manhwa of gods, time rewind, relentless grind."),
    ("I’m the Villainess, So I’m Taming the Final Boss", "Charming villainess story with romance twist."),
    ("Who Made Me a Princess", "Cute father-daughter isekai with royalty and tears."),
    ("Villains Are Destined to Die", "Otome game survival with tragedy and romance."),
    ("Your Throne", "Body-swapping princesses fight for throne and freedom."),
    ("Survive As the Hero’s Wife", "Smart heroine navigates fate and romance in fantasy world."),
    ("Act-Age", "A prodigy actress climbs the industry with raw emotion. Tragic, intense."),
    ("Skip Beat!", "A girl enters showbiz to get revenge on her ex but discovers her own passion."),
    ("Glass Mask", "Classic acting shoujo: rivals, passion, and stage transformations."),
    ("Curtain’s Rise", "A heartfelt manhwa about chasing acting dreams against hardships."),
    ("Honey Blood Beauty Contract", "Top actress meets mysterious contract romance."),
    ("The Beast Must Die", "Drama adaptation backdrop, filled with revenge and performance tension."),

]

def _load_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        # Fallback to a built-in bitmap font if truetype is missing
        return ImageFont.load_default()

# --- Helpers ---
def search_manga_image(title):
    if not SERPAPI_KEY:
        print("[!] SERPAPI_KEY not set; skipping image search.")
        return None
    search_url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": f"{title} manga cover",
        "tbm": "isch",
        "api_key": SERPAPI_KEY,
        "num": 1
    }
    try:
        response = requests.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        results = response.json()
        images = results.get("images_results", [])
        if images:
            return images[0].get("original")
    except Exception as e:
        print(f"[!] SerpAPI error: {e}")
    return None

def download_image(url, path):
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        with open(path, "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"[!] Download error: {e}")
        return False

def add_text_screen(text, output_path):
    width, height = 720, 1024
    bg_color = (0, 0, 0)
    text_color = (255, 255, 255)
    font_size = 40
    font = _load_font(font_size)

    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)

    words = text.split()
    lines = []
    line = ""
    max_width = width - 80
    for word in words:
        test_line = line + word + " "
        bbox = font.getbbox(test_line)
        if bbox[2] - bbox[0] > max_width:
            lines.append(line.strip())
            line = word + " "
        else:
            line = test_line
    if line.strip():
        lines.append(line.strip())

    line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
    total_height = len(lines) * (line_height + 6)
    y = (height - total_height) // 2

    for line in lines:
        text_width = font.getbbox(line)[2] - font.getbbox(line)[0]
        x = (width - text_width) // 2
        draw.text((x, y), line, font=font, fill=text_color)
        y += line_height + 6

    image.save(output_path)

def add_description_to_image(image_path, description, output_path):
    try:
        image = Image.open(image_path).convert("RGBA")
        draw = ImageDraw.Draw(image)
        font_size = max(20, image.width // 20)
        font = _load_font(font_size)

        max_width = image.width - 80
        words = description.split()
        lines = []
        line = ""
        for word in words:
            test_line = line + word + " "
            bbox = font.getbbox(test_line)
            line_width = bbox[2] - bbox[0]
            if line_width > max_width:
                lines.append(line.strip())
                line = word + " "
            else:
                line = test_line
        if line.strip():
            lines.append(line.strip())

        line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
        spacing = 6
        total_text_height = len(lines) * line_height + (len(lines) - 1) * spacing
        text_y = (image.height - total_text_height) // 2
        box_padding = 20
        text_width = max(font.getbbox(l)[2] - font.getbbox(l)[0] for l in lines)

        box_x0 = (image.width - text_width) // 2 - box_padding
        box_y0 = text_y - box_padding
        box_x1 = box_x0 + text_width + 2 * box_padding
        box_y1 = box_y0 + total_text_height + 2 * box_padding

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle([box_x0, box_y0, box_x1, box_y1], fill=(0, 0, 0, 140))
        image = Image.alpha_composite(image, overlay)
        draw = ImageDraw.Draw(image)

        for l in lines:
            lw = font.getbbox(l)[2] - font.getbbox(l)[0]
            text_x = (image.width - lw) // 2
            draw.text((text_x + 2, text_y + 2), l, font=font, fill=(0, 0, 0, 255))
            draw.text((text_x, text_y), l, font=font, fill=(255, 255, 255, 255))
            text_y += line_height + spacing

        image.convert("RGB").save(output_path)
        return True
    except Exception as e:
        print(f"[!] Error adding description: {e}")
        return False

def generate_tts(text, output_path):
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(output_path)
        return True
    except Exception as e:
        print(f"[!] TTS error: {e}")
        return False

def make_zip(output_dir, zip_name):
    with zipfile.ZipFile(zip_name, "w") as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                zipf.write(os.path.join(root, file), file)
    print(f"[+] ZIP created: {zip_name}")

def save_slide_data(slide_data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "slides.json"), "w") as f:
        json.dump(slide_data, f, indent=2)

def send_email_with_slides(slides, title_text):
    if not (EMAIL_SENDER and EMAIL_APP_PASSWORD and EMAIL_RECEIVER):
        print("[!] Email creds not set; skipping email.")
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = title_text
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER

        body = title_text + "\n" + TAGS + "\n\n"
        for slide in slides:
            if "title" in slide and "description" in slide:
                body += f"{slide['title']}: {slide['description']}\n"
        msg.set_content(body)

        for slide in slides:
            if os.path.exists(slide["img"]):
                with open(slide["img"], "rb") as f:
                    img_data = f.read()
                msg.add_attachment(img_data, maintype="image", subtype="jpeg",
                                   filename=os.path.basename(slide["img"]))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        print("[+] Email sent successfully.")
    except Exception as e:
        print(f"[!] Email sending failed: {e}")

# --- Main ---
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    selected = random.sample(MANGA_LIST, min(NUM_RECOMMENDATIONS, len(MANGA_LIST)))
    slide_data = []
    slide_index = 0

    # Title screen
    tiktok_title = random.choice(TIKTOK_TITLES)
    title_img = os.path.join(OUTPUT_DIR, f"manga_final_{slide_index}.jpg")
    title_tts = os.path.join(OUTPUT_DIR, f"tts_{slide_index}.mp3")
    add_text_screen(tiktok_title, title_img)
    generate_tts(tiktok_title, title_tts)
    slide_data.append({"img": title_img, "audio": title_tts})
    slide_index += 1

    # Manga slides
    for (title, desc) in selected:
        print(f"[{slide_index}] Processing: {title}")

        image_url = search_manga_image(title)
        if not image_url:
            print("[!] No image found; skipping.")
            continue

        orig_path = os.path.join(OUTPUT_DIR, f"manga_{slide_index}.jpg")
        final_path = os.path.join(OUTPUT_DIR, f"manga_final_{slide_index}.jpg")
        tts_path = os.path.join(OUTPUT_DIR, f"tts_{slide_index}.mp3")

        if not download_image(image_url, orig_path):
            continue
        if not add_description_to_image(orig_path, desc, final_path):
            continue
        if not generate_tts(f"{title}. {desc}", tts_path):
            continue

        slide_data.append({
            "img": final_path,
            "audio": tts_path,
            "title": title,
            "description": desc
        })
        slide_index += 1

    # Outro
    outro_text = "If you watched till now, you’ll definitely subscribe "
    outro_tts = "If you watched till now, you’ll definitely subscribe."
    outro_img = os.path.join(OUTPUT_DIR, f"manga_final_{slide_index}.jpg")
    outro_audio = os.path.join(OUTPUT_DIR, f"tts_{slide_index}.mp3")
    add_text_screen(outro_text, outro_img)
    generate_tts(outro_tts, outro_audio)
    slide_data.append({"img": outro_img, "audio": outro_audio})
    slide_index += 1

    save_slide_data(slide_data)
    make_zip(OUTPUT_DIR, ZIP_FILE)
    send_email_with_slides(slide_data, tiktok_title)

if __name__ == "__main__":
    main()
