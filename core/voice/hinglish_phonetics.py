from __future__ import annotations

import re
from typing import ClassVar


class HinglishPhoneticEngine:
    """Acoustic Grapheme-to-Phoneme (G2P) and Roman phonetic transliterator for Indian & Hinglish speech."""

    # Protected English / Technical words that MUST NEVER be transliterated
    PROTECTED_TECHNICAL_WORDS: ClassVar[set[str]] = {
        "vs", "code", "studio", "android", "chrome", "spotify", "git", "github",
        "branch", "commit", "push", "pull", "merge", "build", "gradle", "apk",
        "terminal", "command", "powershell", "python", "pytest", "ram", "cpu", "gpu",
        "vram", "disk", "battery", "percent", "volume", "brightness", "wifi", "bluetooth",
        "windows", "youtube", "google", "browser", "search", "screenshot", "camera",
        "desktop", "folder", "file", "files", "app", "application", "task", "planner",
        "status", "error", "warning", "success", "note", "notes", "clock", "timer",
        "alarm", "reminder", "system", "setting", "settings", "mode", "device",
        "keyboard", "mouse", "screen", "monitor", "audio", "video", "network", "ping",
    }

    # Precise Roman Hinglish Word Phonetic Map
    HINGLISH_PHONETIC_DICT: ClassVar[dict[str, str]] = {
        # Pronouns & Auxiliaries
        "hai": "hye",
        "hain": "hyne",
        "hoon": "hoon",
        "hun": "hoon",
        "tha": "thaa",
        "thi": "thee",
        "the": "thay",
        "ho": "hoe",
        "mera": "may-raa",
        "meri": "may-ree",
        "mere": "may-ray",
        "tera": "tay-raa",
        "teri": "tay-ree",
        "tere": "tay-ray",
        "apna": "up-naa",
        "apni": "up-nee",
        "apne": "up-nay",
        "aapka": "aap-kaa",
        "aapki": "aap-kee",
        "aapke": "aap-kay",
        "unka": "oon-kaa",
        "unki": "oon-kee",
        "unke": "oon-kay",
        "iska": "is-kaa",
        "iski": "is-kee",
        "iske": "is-kay",
        "uska": "oos-kaa",
        "uski": "oos-kee",
        "uske": "oos-kay",
        "kya": "kyaa",
        "kyun": "kyoon",
        "kyu": "kyoon",
        "kaise": "kye-say",
        "kaisa": "kye-saa",
        "kaisi": "kye-see",
        "kab": "kub",
        "jab": "jub",
        "tab": "tub",
        "sab": "sub",
        "ab": "ub",
        "kahan": "kahaan",
        "yahan": "yahaan",
        "wahan": "wahaan",
        "jahan": "jahaan",
        "ye": "yay",
        "yeh": "yay",
        "wo": "woh",
        "woh": "woh",

        # Common Verbs & Actions
        "khol": "khole",
        "kholo": "khol-oe",
        "kholna": "khol-naa",
        "chalao": "chulaa-oe",
        "chala": "chulaa",
        "chalu": "chaaloo",
        "kar": "kurr",
        "karo": "kar-oe",
        "kardo": "kurr doe",
        "karna": "kur-naa",
        "karein": "kar-ayn",
        "karen": "kar-ayn",
        "karoon": "kar-oon",
        "raha": "rahaa",
        "rahi": "rahee",
        "rahe": "rahay",
        "batao": "buh-taa-oe",
        "bata": "buh-taa",
        "batana": "buh-taa-naa",
        "bataiye": "buh-taa-ee-yay",
        "dekho": "day-khoe",
        "dekha": "day-khaa",
        "dekhna": "daykh-naa",
        "dikhao": "dikh-aa-oe",
        "dikha": "dikh-aa",
        "samjha": "sum-jhaa",
        "samajh": "sum-ujh",
        "samjhao": "sum-jhaa-oe",
        "sun": "soon",
        "suno": "soon-oe",
        "sunna": "soon-naa",
        "bol": "bohl",
        "bolo": "bohl-oe",
        "boliye": "bohl-ee-yay",
        "ruko": "rook-oe",
        "ruk": "rook",
        "band": "bund",
        "badhao": "budh-aa-oe",
        "kam": "kumm",
        "ghatao": "ghut-aa-oe",
        "rakho": "rukh-oe",
        "rakh": "rukh",
        "rakhiye": "rukh-ee-yay",
        "milte": "mil-tay",
        "mil": "mill",
        "miliye": "mil-ee-yay",
        "dhoond": "dhoond",
        "dhoondo": "dhoond-oe",
        "chalo": "chul-oe",
        "chal": "chull",

        # Conversational Connectors & Greetings
        "namaste": "nuh-mus-tay",
        "namaskar": "nuh-mus-kaar",
        "shukriya": "shook-ree-yaa",
        "dhanyawad": "dhun-yuh-vaad",
        "dhanyavaad": "dhun-yuh-vaad",
        "theek": "theek",
        "thik": "theek",
        "achha": "uch-chhaa",
        "accha": "uch-chhaa",
        "achhi": "uch-chhee",
        "acchi": "uch-chhee",
        "shandaar": "shaan-daar",
        "badhiya": "budh-ee-yaa",
        "zaroor": "zuh-roor",
        "jarur": "zuh-roor",
        "bilkul": "bill-kool",
        "zarurat": "zuh-roo-rut",
        "matlab": "mut-lub",
        "lekin": "lay-kin",
        "magar": "mug-ur",
        "par": "purr",
        "pe": "pay",
        "mein": "may",
        "mai": "may",
        "main": "main",
        "hum": "humm",
        "aap": "aap",
        "tum": "toom",
        "tu": "too",
        "bhai": "bhye",
        "yaar": "yaarr",
        "dost": "dohst",
        "sahab": "saa-hub",
        "sirf": "sirff",
        "zyada": "zyaa-daa",
        "jyada": "zyaa-daa",
        "thoda": "thoh-daa",
        "thodi": "thoh-dee",
        "thode": "thoh-day",
        "bohot": "boh-hut",
        "bahut": "buh-hoot",
        "abhi": "ubh-ee",
        "kabhi": "kub-hee",
        "pehle": "peh-lay",
        "baad": "baad",
        "aaj": "aaj",
        "kal": "kull",
        "parso": "pur-soe",
        "chup": "choop",
        "bas": "buss",
        "waise": "wye-say",
        "sahi": "suh-hee",
        "galat": "gull-ut",
        "aasan": "aa-saan",
        "mushkil": "moosh-kill",
    }

    # Devanagari Unicode transliteration mapping
    DEVANAGARI_MAP: ClassVar[dict[str, str]] = {
        "नमस्ते": "nuh-mus-tay",
        "नमस्कार": "nuh-mus-kaar",
        "हाँ": "haan",
        "हां": "haan",
        "नहीं": "na-heen",
        "धन्यवाद": "dhun-yuh-vaad",
        "शुक्रिया": "shook-ree-yaa",
        "अच्छा": "uch-chhaa",
        "अच्छी": "uch-chhee",
        "ठीक": "theek",
        "खोलो": "khol-oe",
        "खोल": "khole",
        "चलाओ": "chulaa-oe",
        "करो": "kar-oe",
        "कर": "kurr",
        "रहा": "rahaa",
        "रही": "rahee",
        "रहे": "rahay",
        "हूँ": "hoon",
        "हूं": "hoon",
        "है": "hye",
        "हैं": "hyne",
        "क्या": "kyaa",
        "क्यों": "kyoon",
        "कैसे": "kye-say",
        "बताओ": "buh-taa-oe",
        "देखो": "day-khoe",
        "शानदार": "shaan-daar",
        "बढ़िया": "budh-ee-yaa",
        "ज़रूर": "zuh-roor",
        "बिल्कुल": "bill-kool",
        "रुकिए": "rook-ee-yay",
        "रुपये": "roo-pay",
    }

    @classmethod
    def transliterate_for_tts(cls, text: str) -> str:
        """Convert Roman Hinglish and Devanagari into acoustic phonetic spellings for natural English TTS."""
        if not text.strip():
            return text

        # 1. First replace exact Devanagari full words
        result = text
        for dev, phon in cls.DEVANAGARI_MAP.items():
            result = result.replace(dev, phon)

        # 2. Tokenize preserving punctuation and casing
        def _replace_word(match: re.Match[str]) -> str:
            word = match.group(0)
            lowered = word.lower()

            # If protected technical English word, keep as is
            if lowered in cls.PROTECTED_TECHNICAL_WORDS:
                return word

            # If in phonetic dictionary, replace
            if lowered in cls.HINGLISH_PHONETIC_DICT:
                phon = cls.HINGLISH_PHONETIC_DICT[lowered]
                # Match title casing if applicable
                if word.istitle():
                    return phon.capitalize()
                return phon

            return word

        # Replace word tokens
        result = re.sub(r"\b[a-zA-Z]+\b", _replace_word, result)

        # 3. Clean up common Hinglish phonetic compound contractions
        result = re.sub(r"\bkar\s*raha\s*hoon\b", "kurr rahaa hoon", result, flags=re.IGNORECASE)
        result = re.sub(r"\bkhol\s*raha\s*hoon\b", "khole rahaa hoon", result, flags=re.IGNORECASE)
        result = re.sub(r"\bkhol\s*diya\s*hai\b", "khole diyaa hye", result, flags=re.IGNORECASE)
        result = re.sub(r"\bkar\s*diya\s*hai\b", "kurr diyaa hye", result, flags=re.IGNORECASE)
        result = re.sub(r"\bchalu\s*kar\s*diya\b", "chaaloo kurr diyaa", result, flags=re.IGNORECASE)

        return result
