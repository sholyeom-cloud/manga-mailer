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
    ("Smoking Behind the Supermarket with You", "Two tired adults, one smoking spot, and a slow-burn love."),
    ("Futari no Renai Shoka", "Bookstore boy meets literary girl. Age gap? Maybe. Chemistry? Definitely."),
    ("Najica (Salad Days)", "Short stories of love and high school/college life in vivid, heartfelt arcs."),
    ("Missions of Love", "Cold junior-higher uses romance 'missions' to reveal feelings. Predictably chaotic."),
    ("Taishou Otome Otogibanashi", "Historical sweetness, retro flair and love letters under moonlight."),
    ("Otoyomegatari", "Brides in Central Asia: politics, tradition and delicate romance."),
    ("Futari Ashita mo Sorenari ni", "Adult couple, real problems, relatable tenderness."),
    ("Kimi wa Houkago Insomnia", "Night-owl romance between two teens who only meet after school."),
    ("Senryuu Shoujo", "Tiny poems, big feelings: a shy girl finds love via haiku humor."),
    ("Aharen-san wa Hakarenai", "Tiny tsundere, big cuteness, embarrassing misunderstandings."),
    ("Yagate Kimi ni Naru", "Yuri slow-burn between shy girls discovering real feelings."),
    ("Yancha Gal no Anjou-san", "Tsundere gal teases nerd. Eventually she can't resist."),
    ("Namaikizakari.", "Tomboy cheerleader vs basketball captain – fiery rivalry, fiery romance."),
    ("Dengeki Daisy", "Protective guy sends secret texts. She sends sass back."),
    ("Fuufu Ijou, Koibito Miman", "Fake-married high school couple. What could go wrong?"),
    ("Mijuku na Futari de Gozaimasu ga", "Married teens struggle to be romantic – awkward and sweet."),
    ("Neko no Otera no Chion-san", "Quiet Buddhist temple girl and guy come together in silent moments."),
    ("Suki na Ko ga Megane wo Wasureta", "Girl forgets glasses. Boy notices, she blushes, you swoon."),
    ("Fujimura-kun Mates", "Bully becomes sweet after confession. Rom-com cliché done right."),
    ("Rough Sketch Senpai", "Accidental nude sketch? Her embarrassment, his compliments."),
    ("Koi wa Sekai Seifuku no Ato de", "Supervillain and idol secretly date. World domination or love?"),
    ("Jumyou wo Kaitotte Moratta", "She sells lifespan. He wants more. Dark but romantic."),
    ("Yugami-kun ni wa Tomodachi ga Inai", "Weird loner boy and popular girl. Friendship becomes more."),
    ("Tsubaki-chou Lonely Planet", "Slow-burn friendships, overseas study, first love."),
    ("The Last Game", "High-stakes rivalry in tennis triggers unexpected romance."),
    ("Horimiya", "Normal teens, hidden sides, big chemistry."),
    ("Home Office Romance", "Adult coworkers, WFH chaos and sparks."),
    ("Our Precious Conversations", "Short, sweet commuter romance with big feels."),
    ("The Fragrant Flower Blooms With Dignity", "Elegant modern rom-com with refined characters."),
    ("You and I Are Polar Opposites", "Opposites attract in high school. Cute plus chemistry."),
    ("The Dangers in My Heart", "Middle-schooler with dark imagination finds romance nearby."),
    ("Call of the Night", "Vampire romance under neon lights, soft and shadowy."),
    ("Even If You Slit My Mouth", "Supernatural fluff meets forbidden attraction."),
    ("Giji Harem", "Reluctant harem, surprisingly romantic and hilarious."),
    ("Doujima-kun wa Doujinai", "Gyaru x honor student matchup? Funny and satisfying."),
    ("Blue Box", "Sports romance + basketball + tennis = heart on court."),
    ("Tonikaku Cawaii", "Married-at-first-sight cuteness overload."),
    ("Taiyou no Ie", "50 chapters of slow slice-of-life love."),
    ("Pretty Face", "Boys fall in love with girl who looks like another."),
    ("Hentai Ouji to Warawanai Neko", "Silent, deadpan girl eventually warms up."),
    ("Kami-sama Kiss", "God of love messes up temple girl’s life… romantically."),
    ("Lovely Complex", "Tall girl & short guy battle height stereotypes and find love."),
    ("Fruits Basket", "Cursed family, deep bonds and shy romance healing all wounds."),
    ("Kimi ni Todoke", "Misunderstood girl blossoms thanks to gentle boy."),
    ("ReLIFE", "Second chance at youth. Romance and redemption."),
    ("Moon on a Rainy Night", "Gentle yuri between adult librarian and woman."),
    ("Insomniacs After School", "Late-night school rooftop confession vibes."),
    ("My Senpai is Annoying", "Office romance with teasing senior and obedient junior."),
    ("Glasses with a Chance of Delinquent", "Class rep falls for bad boy… who secretly needs her."),
    ("Honey Lemon Soda", "Shy girl meets sparkling cheer boy. Bright, sugary rom-com."),
    ("Koiwazurai no Ellie", "Cutesy, slow branded yuri with café vibes."),
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
