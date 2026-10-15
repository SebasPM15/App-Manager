import os
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "lucide.ttf")
RENDER_SIZE = 96

CODEPOINTS = {
    "smartphone":       0xE166,
    "dashboard":        0xE1C0,
    "apps":             0xE42A,
    "remote":           0xE489,
    "terminal":         0xE209,
    "refresh":          0xE148,
    "play":             0xE13F,
    "camera":           0xE068,
    "clock":            0xE08B,
    "power":            0xE143,
    "chevron-right":    0xE073,
    "chevron-down":     0xE071,
    "home":             0xE0F8,
    "recents":          0xE456,
    "search":           0xE154,
    "upload":           0xE19D,
    "wifi":             0xE1AD,
    "wifi-off":         0xE1AE,
    "battery":          0xE058,
    "gauge":            0xE1BE,
    "trash":            0xE18D,
    "settings":         0xE244,
    "folder":           0xE246,
    "signal":           0xE25E,
    "zap":              0xE1B3,
    "arrow-left":       0xE04C,
    "arrow-right":      0xE04D,
    "arrow-up":         0xE04E,
    "arrow-down":       0xE046,
    "cable":            0xE4E7,
    "sliders":          0xE299,
    "sync":             0xE14C,
    "mobile-data":      0xE0EB,
    "stop":             0xE16A,
    "sparkles":         0xE416,
    "command":          0xE09E,
    "download":         0xE0B6,
}

_font_cache: ImageFont.FreeTypeFont | None = None
_image_cache: dict[tuple, ctk.CTkImage] = {}


def _font() -> ImageFont.FreeTypeFont:
    global _font_cache
    if _font_cache is None:
        _font_cache = ImageFont.truetype(FONT_PATH, RENDER_SIZE)
    return _font_cache


def icon(name: str, size: int = 16, color: str = "#ffffff") -> ctk.CTkImage | None:
    key = (name, size, color)
    cached = _image_cache.get(key)
    if cached is not None:
        return cached
    code = CODEPOINTS.get(name)
    if code is None or not os.path.isfile(FONT_PATH):
        return None
    canvas = RENDER_SIZE + 8
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((canvas / 2, canvas / 2), chr(code), font=_font(), fill=color, anchor="mm")
    result = ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
    _image_cache[key] = result
    return result
