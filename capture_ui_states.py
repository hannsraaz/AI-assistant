from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def render_ui_card(
    state: str,
    badge_text: str,
    badge_color: str,
    status_text: str,
    user_text: str,
    friday_text: str,
    output_filename: str,
) -> None:
    width, height = 460, 580
    img = Image.new("RGB", (width, height), color="#0d1117")
    draw = ImageDraw.Draw(img)

    # Fonts
    try:
        font_title = ImageFont.truetype("segoeui.ttf", 22)
        font_badge = ImageFont.truetype("segoeuib.ttf", 11)
        font_status = ImageFont.truetype("segoeui.ttf", 13)
        font_chat = ImageFont.truetype("segoeui.ttf", 14)
        font_pill = ImageFont.truetype("segoeuib.ttf", 11)
    except Exception:
        font_title = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        font_status = ImageFont.load_default()
        font_chat = ImageFont.load_default()
        font_pill = ImageFont.load_default()

    # Header
    draw.text((20, 16), "FRIDAY", fill="#00d2ff", font=font_title)

    # Badge
    badge_w, badge_h = 80, 24
    bx, by = width - 20 - badge_w, 18
    draw.rounded_rectangle([bx, by, bx + badge_w, by + badge_h], radius=4, fill="#161b22", outline="#30363d")
    draw.text((bx + 12, by + 4), badge_text, fill=badge_color, font=font_badge)

    # Glowing Orb Area (cx=230, cy=130)
    cx, cy = width // 2, 130
    if state == "idle":
        # Breathing Cyan Orb
        draw.ellipse([cx - 50, cy - 50, cx + 50, cy + 50], fill="#12202e", outline=None)
        draw.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill="#1f6feb", outline="#00d2ff", width=3)
    elif state == "listening":
        # Pulsing Red Orb
        draw.ellipse([cx - 58, cy - 58, cx + 58, cy + 58], fill="#381018", outline=None)
        draw.ellipse([cx - 44, cy - 44, cx + 44, cy + 44], fill="#ff0055", outline="#ff7b72", width=3)
    elif state == "thinking":
        # Amber Spinning Arc
        draw.ellipse([cx - 48, cy - 48, cx + 48, cy + 48], fill="#251e10", outline=None)
        draw.arc([cx - 44, cy - 44, cx + 44, cy + 44], start=30, end=240, fill="#e3b341", width=5)
    elif state == "speaking":
        # Expanding Cyan Soundwave
        draw.ellipse([cx - 56, cy - 56, cx + 56, cy + 56], fill="#0d2838", outline=None)
        draw.ellipse([cx - 44, cy - 44, cx + 44, cy + 44], fill="#00d2ff", outline="#79c0ff", width=3)

    # Status Label
    draw.text((width // 2 - 120, 205), status_text, fill="#8b949e", font=font_status)

    # Chat Container
    chat_x, chat_y, chat_w, chat_h = 20, 235, width - 40, 220
    draw.rounded_rectangle([chat_x, chat_y, chat_x + chat_w, chat_y + chat_h], radius=8, fill="#161b22", outline="#30363d")

    draw.text((chat_x + 16, chat_y + 16), f"You: {user_text}", fill="#79c0ff", font=font_chat)
    draw.line([chat_x + 16, chat_y + 42, chat_x + chat_w - 16, chat_y + 42], fill="#21262d", width=1)
    draw.text((chat_x + 16, chat_y + 54), friday_text, fill="#f0f6fc", font=font_chat)

    # Quick Action Pills
    pills = ["Mute", "Screenshot", "PC Stats", "Stop Audio"]
    px = 20
    py = 470
    for p in pills:
        pw = 88
        draw.rounded_rectangle([px, py, px + pw, py + 26], radius=4, fill="#21262d", outline="#30363d")
        draw.text((px + 12, py + 5), p, fill="#c9d1d9", font=font_pill)
        px += pw + 12

    # Bottom Input Bar
    bx, by = 20, 515
    # Mic Button
    draw.rounded_rectangle([bx, by, bx + 70, by + 36], radius=4, fill="#00d2ff", outline=None)
    draw.text((bx + 12, by + 9), "🎙️ Talk", fill="#0d1117", font=font_pill)

    # Input Box
    draw.rounded_rectangle([bx + 80, by, width - 20 - 45, by + 36], radius=4, fill="#21262d", outline="#30363d")
    draw.text((bx + 90, by + 9), "Ask Friday anything...", fill="#8b949e", font=font_chat)

    # Send Button
    draw.rounded_rectangle([width - 20 - 36, by, width - 20, by + 36], radius=4, fill="#238636", outline=None)
    draw.text((width - 20 - 24, by + 9), "➤", fill="#ffffff", font=font_chat)

    img.save(output_filename, "PNG")
    print(f"  [OK] Saved {output_filename}")


def generate_all_ui_screenshots() -> None:
    print("Generating UI state screenshots...")

    render_ui_card(
        state="idle",
        badge_text="READY",
        badge_color="#00ffa3",
        status_text="Say 'Hey Jarvis' or click orb",
        user_text="...",
        friday_text="Friday is ready to assist you. Ask a question or control your PC.",
        output_filename="ui_01_idle.png",
    )

    render_ui_card(
        state="listening",
        badge_text="LISTENING",
        badge_color="#ff0055",
        status_text="Listening for your command...",
        user_text="What's my battery percentage?",
        friday_text="Listening...",
        output_filename="ui_02_listening.png",
    )

    render_ui_card(
        state="thinking",
        badge_text="THINKING",
        badge_color="#e3b341",
        status_text="Processing command...",
        user_text="Set volume to 40 percent and show desktop",
        friday_text="Processing request...",
        output_filename="ui_03_thinking.png",
    )

    render_ui_card(
        state="speaking",
        badge_text="SPEAKING",
        badge_color="#00d2ff",
        status_text="Speaking response...",
        user_text="What time is it?",
        friday_text="It is 1:20 AM right now.",
        output_filename="ui_04_speaking.png",
    )

    print("All 4 UI state screenshots generated successfully!")


if __name__ == "__main__":
    generate_all_ui_screenshots()
