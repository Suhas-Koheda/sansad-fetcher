import re
from pathlib import Path

class SansadDecoder:
    MAP_2019 = {
        "E": "ध्",
        "y": "य",
        "F": "क्ष",
        "O": "र्",
        "P": "ी",
        "U": "च्",
    }

    MAP_2020 = {
        "<": "ध्",
        "=": "क्ष",
        "_": "श्र",
        "h": "प्र",
        "i": "ज्ञ",
        "m": "द्व",
    }

    MAP_2021 = {
        "D": "ध्",
        "E": "क्ष",
        "fी": "श्री",
        "f": "श्र",
        "V": "स्",
        "l": "क्त",
        "p": "रू",
        "mq": "में",
        "t": "स्थ",
        "'": "ि",
    }

    MAP_2022 = {
        "D": "ध्",
        "E": "क्ष",
        "b": "स्",
        "l": "ु",
        "t": "क्ष",
        "u": "श्च",
        "w": "श्",
        "{": "ों",
        "~": "व्य",
        "v": "स्थ",
        "\x80": "ें",
        "\x81": "द्र",
    }

    MAP_2023_2026 = {
        "Å": "ध्",
        "±": "क्ष",
        "ò": "ु",
        "ª": "र्",
        "ÿ": "प्र",
        "Æ": "न्",
        "é": "ीं",
        "Â": "त्",
        "Õ": "ष्",
        "ů": "ट्र",
        "Ō": "ों",
        "§": "ैं",
        "Ö": "स्",
        "ý": "त्र",
        "ł": "रू",
        "¤": "ें",
        "å": "िर",
    }

    MAP_AJ = {
        "@": "ध्",
        "A": "क्ष",
        "K": "ख्",
        "G": "प्र",
        "D": "श्र",
        "O": "श्र",
        "T": "ं",
        "^": "व्",
        "d": "ध्",
        "e": "क्ष",
        "i": "ष्",
        "j": "ें",
        "q": "र्",
        "p": "स्",
        "x": "ज्ञ",
        "z": "ी",
        "{": "रू",
        "}": "ीं",
        "~": "ब्",
        "\x7f": "क्",
        "\x82": "ं",
        "\x84": "श्च",
        "\x85": "रू",
        "\x88": "िर",
        "\x8a": "ैं",
        "\x8b": "त्र",
        "\x8d": "ू",
        "\x90": "क्त",
        "\x93": "द्या",
        "\x94": "ों",
    }

    MAP_AK = {
        "Lी": "श्री",
        "L": "ख्",
        "I": "ध्",
        "J": "क्ष",
        "H": "प्र",
        "O": "श्र",
        "_": "ध्",
        "`": "क्ष",
        "q": "ें",
        "f": "ें",
        "p": "ु",
        "n": "र्",
        "r": "क्वे",
        "s": "श्च",
    }

    MAP_URDU = {}

    @classmethod
    def detect_profile(cls, text, pdf_path=None):
        if any('\u0600' <= c <= '\u06FF' for c in text):
            return "URDU"
            
        # Check other scripts (Bengali, Tamil, etc.)
        if any('\u0980' <= c <= '\u0FFF' for c in text if not ('\u0900' <= c <= '\u097F')):
            return "OTHER"
            
        if pdf_path:
            # Determine profile by year from path
            path_str = str(pdf_path)
            if "2019" in path_str:
                return "2019"
            elif "2020" in path_str:
                # Check for AJ specific signature
                if "@" in text or "अ@य" in text:
                    return "AJ"
                return "2020"
            elif "2021" in path_str:
                return "2021"
            elif "2022" in path_str:
                # Check for AK specific signature
                if "L_" in text or "अIयJ" in text or "Lी" in text:
                    return "AK"
                return "2022"
            elif any(yr in path_str for yr in ["2023", "2024", "2025", "2026"]):
                return "2023_2026"
                
        # Fallback heuristic
        devanagari_count = len(re.findall(r"[\u0900-\u097F]", text))
        if devanagari_count < 5:
            return None
            
        if any(c in text for c in "Å±òªÿÆéÂÕůŌ§Öýł¤å"):
            return "2023_2026"
        if "L_" in text or "अIयJ" in text or "Lी" in text:
            return "AK"
        if "@" in text or "अ@य" in text or "\x85" in text:
            return "AJ"
        if any(c in text for c in "\x80\x81~{uwb"):
            return "2022"
        if any(c in text for c in "DfVlpmt'"):
            return "2021"
        if any(c in text for c in "<=_him"):
            return "2020"
        return "2019"

    @classmethod
    def decode(cls, text, pdf_path=None):
        profile = cls.detect_profile(text, pdf_path)
        if not profile or profile in ["URDU", "OTHER"]:
            return text
            
        if profile == "2019":
            mapping = cls.MAP_2019
        elif profile == "2020":
            mapping = cls.MAP_2020
        elif profile == "2021":
            mapping = cls.MAP_2021
        elif profile == "2022":
            mapping = cls.MAP_2022
        elif profile == "2023_2026":
            mapping = cls.MAP_2023_2026
        elif profile == "AJ":
            mapping = cls.MAP_AJ
        elif profile == "AK":
            mapping = cls.MAP_AK
        else:
            return text
            
        tokens = re.split(r"(\s+)", text)
        decoded_tokens = []
        for t in tokens:
            if not t.strip():
                decoded_tokens.append(t)
            else:
                word = t
                if profile == "AJ":
                    word = word.replace("\x85प", "रूप")
                    word = word.replace("…प", "रूप")
                    word = word.replace("मf", "में")
                elif profile == "AK":
                    word = word.replace("HI", "प्रश्न")
                    word = word.replace("मf", "में")
                    word = word.replace("\\y", "व्य")
                    word = word.replace("\\य", "व्य")
                    
                # Decode only if token has Devanagari character to preserve English
                if any('\u0900' <= c <= '\u097F' for c in word):
                    for k, v in mapping.items():
                        word = word.replace(k, v)
                    decoded_tokens.append(word)
                else:
                    decoded_tokens.append(t)
        return "".join(decoded_tokens)