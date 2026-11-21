"""
Settings editor (v4) — baca/tulis .env dari UI.

- Hanya kunci di SCHEMA yang boleh diubah (whitelist).
- Nilai divalidasi (tipe, pilihan, tanpa baris baru agar tidak bisa menyisipkan variabel lain).
- .env ditulis ulang dengan mempertahankan komentar & urutan; kunci baru ditambahkan di akhir.
- Perubahan langsung diterapkan ke modul config yang sedang berjalan (tanpa restart).
- API key tidak pernah dikembalikan utuh — hanya status + versi tersamar.
"""
from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional

import config

ENV_PATH = config.BASE_DIR / ".env"
EXAMPLE_PATH = config.BASE_DIR / ".env.example"
_LOCK = threading.Lock()

_PROVIDERS = ["Groq", "OpenAI", "Anthropic", "Gemini", "Antigravity", "DeepSeek", "Mistral", "OpenRouter", "Ollama", "Custom"]

# key, grup, label, tipe, opsi/rentang, bantuan
SCHEMA: List[Dict] = [
    # --- AI
    {"key": "AI_PROVIDER", "group": "AI", "label": "Provider AI utama", "type": "enum", "options": _PROVIDERS},
    {"key": "LLM_MODEL", "group": "AI", "label": "Model", "type": "str"},
    {"key": "AI_FALLBACK_PROVIDERS", "group": "AI", "label": "Provider cadangan", "type": "str",
     "help": "Dipakai bila provider utama gagal. Format Provider:model dipisah koma, mis. OpenAI:gpt-4o, Gemini"},
    {"key": "AI_MOMENT_FINDER", "group": "AI", "label": "AI memilih momen", "type": "bool", "help": "AI membaca seluruh transkrip lalu memilih momen terbaik"},
    {"key": "AI_CLIP_PACKAGING", "group": "AI", "label": "AI menulis judul, hook & caption", "type": "bool"},
    {"key": "AI_MAX_CANDIDATES", "group": "AI", "label": "Kandidat momen yang dinilai AI", "type": "int", "min": 0, "max": 200},
    # --- API keys
    {"key": "ANTHROPIC_API_KEY", "group": "API key", "label": "Anthropic (Claude)", "type": "secret"},
    {"key": "OPENAI_API_KEY", "group": "API key", "label": "OpenAI", "type": "secret"},
    {"key": "GEMINI_API_KEY", "group": "API key", "label": "Google Gemini", "type": "secret", "help": "Gratis di aistudio.google.com/apikey"},
    {"key": "GROQ_API_KEY", "group": "API key", "label": "Groq", "type": "secret", "help": "Gratis di console.groq.com"},
    {"key": "DEEPSEEK_API_KEY", "group": "API key", "label": "DeepSeek", "type": "secret"},
    {"key": "MISTRAL_API_KEY", "group": "API key", "label": "Mistral", "type": "secret"},
    {"key": "OPENROUTER_API_KEY", "group": "API key", "label": "OpenRouter", "type": "secret"},
    {"key": "ELEVENLABS_API_KEY", "group": "API key", "label": "ElevenLabs", "type": "secret", "help": "Suara, clone suara, SFX, musik, dan transkripsi"},
    {"key": "POLLINATIONS_TOKEN", "group": "API key", "label": "Token Pollinations", "type": "secret",
     "help": "Opsional. Tanpa token, gambar dibatasi 1 per 45 detik. Daftar di enter.pollinations.ai"},
    {"key": "PEXELS_API_KEY", "group": "API key", "label": "Pexels", "type": "secret", "help": "Footage & foto stok gratis. Key di pexels.com/api"},
    {"key": "PIXABAY_API_KEY", "group": "API key", "label": "Pixabay", "type": "secret", "help": "Footage & foto stok gratis. Key di pixabay.com/api/docs"},
    {"key": "YOUTUBE_API_KEY", "group": "API key", "label": "YouTube Data API", "type": "secret", "help": "Opsional, untuk Analitik Viral. Tanpa key memakai pencarian yt-dlp"},
    {"key": "GLOBAL_HASHTAGS", "group": "Upload otomatis", "label": "Hashtag tambahan untuk semua upload", "type": "str",
     "help": "Ditambahkan ke caption setiap upload (otomatis maupun manual), mis. #namachannel #fyp"},
    {"key": "TIKTOK_PROFILE", "group": "Upload otomatis", "label": "Username TikTok (untuk belajar jam terbaik)", "type": "str",
     "help": "Mis. @namakamu — views 24 jam tiap upload dibaca dari profil publik untuk menemukan jam paling ramai channel-mu"},
    {"key": "AUTO_PUBLISH_PER_DAY", "group": "Upload otomatis", "label": "Maks upload otomatis per hari (per platform)", "type": "int", "min": 1, "max": 8},
    {"key": "AUTO_PUBLISH_MIN_GAP_H", "group": "Upload otomatis", "label": "Jarak minimal antar upload (jam)", "type": "float", "min": 0.5, "max": 12},
    {"key": "KLING_API_KEY", "group": "API key", "label": "Kling AI (video)", "type": "secret",
     "help": "Video AI gambar→video / teks→video (Kling 3.0). API Key dari konsol developer Kling (bukan AK/SK lama)"},
    # --- Media AI (v6)
    {"key": "TTS_PROVIDER", "group": "Suara & gambar AI", "label": "Mesin suara", "type": "enum", "options": ["elevenlabs", "edge", "openai", "gemini"],
     "labels": {"elevenlabs": "ElevenLabs (paling natural)", "edge": "Edge TTS (gratis, tanpa key)", "openai": "OpenAI", "gemini": "Gemini"}},
    {"key": "TTS_VOICE", "group": "Suara & gambar AI", "label": "Suara default", "type": "str",
     "help": "ElevenLabs: voice_id. Edge: mis. id-ID-ArdiNeural. OpenAI: nova. Gemini: Kore"},
    {"key": "IMAGE_PROVIDER", "group": "Suara & gambar AI", "label": "Mesin gambar", "type": "enum", "options": ["", "gemini", "openai", "pollinations", "card"],
     "labels": {"": "Otomatis (Gemini bila ada key, lalu Pollinations)", "gemini": "Gemini", "openai": "OpenAI", "pollinations": "Pollinations (gratis)", "card": "Kartu teks (tanpa AI)"}},
    {"key": "IMAGE_MODEL", "group": "Suara & gambar AI", "label": "Model gambar (koneksi)", "type": "str",
     "help": "Dipakai bila mesin gambar adalah Koneksi API, mis. gpt-image-2"},
    {"key": "GEMINI_IMAGE_MODEL", "group": "Suara & gambar AI", "label": "Model gambar Gemini", "type": "str"},
    {"key": "OPENAI_IMAGE_MODEL", "group": "Suara & gambar AI", "label": "Model gambar OpenAI", "type": "enum", "options": ["gpt-image-1", "gpt-image-1-mini", "dall-e-3"]},
    {"key": "OPENAI_TTS_MODEL", "group": "Suara & gambar AI", "label": "Model suara OpenAI", "type": "enum", "options": ["gpt-4o-mini-tts", "tts-1", "tts-1-hd"]},
    {"key": "GEMINI_TTS_MODEL", "group": "Suara & gambar AI", "label": "Model suara Gemini", "type": "str"},
    {"key": "ELEVENLABS_TTS_MODEL", "group": "Suara & gambar AI", "label": "Model suara ElevenLabs", "type": "enum",
     "options": ["eleven_multilingual_v2", "eleven_v3", "eleven_flash_v2_5", "eleven_turbo_v2_5"],
     "labels": {"eleven_multilingual_v2": "Multilingual v2 (disarankan)", "eleven_v3": "v3 (ekspresif, lebih lambat)",
                "eleven_flash_v2_5": "Flash v2.5 (tercepat)", "eleven_turbo_v2_5": "Turbo v2.5"}},
    # --- Transkripsi
    {"key": "WHISPER_DEVICE", "group": "Transkripsi", "label": "Mesin transkripsi", "type": "enum", "options": ["elevenlabs", "auto", "cuda", "cpu", "groq"],
     "labels": {"elevenlabs": "ElevenLabs Scribe (paling akurat)", "auto": "Whisper di GPU, CPU bila tidak ada", "cuda": "Whisper di GPU NVIDIA",
                "cpu": "Whisper di CPU (lambat)", "groq": "Groq Whisper (cloud)"},
     "help": "Scribe menangkap ucapan lebih lengkap dan timestamp-nya pas, jadi subtitle tidak nyangkut. Bila gagal, otomatis pindah ke Whisper."},
    {"key": "ELEVENLABS_STT_MODEL", "group": "Transkripsi", "label": "Model Scribe", "type": "enum", "options": ["scribe_v2", "scribe_v1"],
     "labels": {"scribe_v2": "Scribe v2 (disarankan)", "scribe_v1": "Scribe v1"}},
    {"key": "WHISPER_LANGUAGE", "group": "Transkripsi", "label": "Bahasa video", "type": "enum", "options": ["", "id", "en", "ms", "jw"],
     "labels": {"": "Deteksi otomatis", "id": "Indonesia", "en": "English", "ms": "Melayu", "jw": "Jawa"}},
    {"key": "WHISPER_MODEL", "group": "Transkripsi", "label": "Model Whisper (cadangan)", "type": "enum", "options": ["tiny", "base", "small", "medium", "large-v3-turbo", "large-v3"],
     "labels": {"large-v3-turbo": "large-v3-turbo (disarankan)"}},
    {"key": "WHISPER_COMPUTE_TYPE", "group": "Transkripsi", "label": "Presisi Whisper", "type": "enum", "options": ["int8", "int8_float16", "float16", "float32"],
     "labels": {"int8": "int8 (hemat memori, disarankan)", "int8_float16": "int8_float16", "float16": "float16 (butuh VRAM besar)", "float32": "float32 (paling berat)"}},
    {"key": "WHISPER_BEAM_SIZE", "group": "Transkripsi", "label": "Ketelitian Whisper (beam)", "type": "int", "min": 1, "max": 10},
    {"key": "WHISPER_BATCH_SIZE", "group": "Transkripsi", "label": "Batch Whisper di GPU", "type": "int", "min": 0, "max": 64},
    # --- Editing (v4)
    {"key": "EDIT_STYLE", "group": "Gaya editing", "label": "Preset", "type": "enum", "options": ["minimal", "dinamis", "maksimal"],
     "labels": {"minimal": "Minimal", "dinamis": "Dinamis (disarankan)", "maksimal": "Maksimal"},
     "help": "Minimal: potong + caption + audio rapi + kamera ikut pembicara. Dinamis: + potong jeda, zoom, cold open + rewind, caption animasi + emoji, sound design, b-roll, layar goyang, nama pembicara, sensor kata kasar. Maksimal: + freeze frame, whoosh di tiap zoom & warna vibrant"},
    {"key": "JUMP_CUT_MAX_GAP", "group": "Gaya editing", "label": "Jeda yang dipotong", "type": "float", "min": 0.2, "max": 3.0, "help": "Detik. Hening lebih lama dari ini dipotong"},
    {"key": "PROGRESS_BAR_COLOR", "group": "Gaya editing", "label": "Warna progress bar", "type": "color"},
    {"key": "END_SCREEN_TEXT", "group": "Gaya editing", "label": "Teks ajakan di akhir klip", "type": "str"},
    # --- Render
    {"key": "CAMPAIGN_DEFAULT_PRESET", "group": "Render", "label": "Preset campaign default", "type": "text",
     "help": "Nama file di folder presets/ yang dipakai otomatis oleh Campaign dan Live spike"},
    {"key": "USE_NVENC", "group": "Render", "label": "Render pakai GPU NVIDIA", "type": "bool"},
    {"key": "DOWNLOAD_MAX_HEIGHT", "group": "Render", "label": "Kualitas download sumber", "type": "enum",
     "options": ["1080", "1440", "2160", "0"],
     "labels": {"1080": "1080p60 (hemat)", "1440": "1440p60", "2160": "2160p (4K)", "0": "Tertinggi"},
     "help": "Resolusi maksimum saat mengunduh video sumber. 1080p60 cukup untuk output 1080x1920."},
    {"key": "ENCODE_CQ", "group": "Render", "label": "CQ/CRF encoder", "type": "enum",
     "options": ["0", "14", "18", "19", "20"],
     "labels": {"0": "Ikut codebase (14)", "14": "14 (paling besar)", "18": "18", "19": "19", "20": "20 (paling hemat)"},
     "help": "Semakin kecil = kualitas lebih tinggi tapi file lebih besar. 18–20 disarankan untuk hemat disk."},
    {"key": "PARALLEL_CLIPS", "group": "Render", "label": "Klip dirender bersamaan", "type": "int", "min": 1, "max": 8},
    {"key": "SCENE_SNAP_ENABLED", "group": "Render", "label": "Potong tepat di pergantian scene", "type": "bool"},
    {"key": "PEAK_THUMBNAIL", "group": "Render", "label": "Thumbnail dari momen puncak", "type": "bool"},
    {"key": "ENABLE_HOOK_PUNCH", "group": "Render", "label": "Zoom kejut di awal klip", "type": "bool"},
    {"key": "KEEP_SOURCE_VIDEO", "group": "Render", "label": "Simpan video sumber", "type": "bool"},
    # --- Publish
    {"key": "ENABLE_PUBLISH_PACKAGE", "group": "Upload", "label": "Buat paket upload per platform", "type": "bool"},
    {"key": "YOUTUBE_PRIVACY", "group": "Upload", "label": "Privasi upload YouTube", "type": "enum", "options": ["public", "unlisted", "private"],
     "labels": {"public": "Publik", "unlisted": "Tidak publik (unlisted)", "private": "Pribadi"}},
    {"key": "YOUTUBE_UPLOAD_METHOD", "group": "Upload", "label": "Metode upload YouTube", "type": "enum",
     "options": ["auto", "api", "browser"],
     "labels": {"auto": "Otomatis (API bila client_secret ada)", "api": "YouTube Data API (resmi)", "browser": "Browser headless (cookie)"},
     "help": "Browser headless = otomatisasi tidak resmi; bisa berhenti bekerja atau memicu batasan akun jika tampilan YouTube Studio berubah."},
    {"key": "YOUTUBE_CLIENT_SECRET_FILE", "group": "Upload", "label": "File client_secret.json YouTube", "type": "path"},
    {"key": "TIKTOK_COOKIES_FILE", "group": "Upload", "label": "File cookies.txt TikTok", "type": "path"},
    {"key": "TIKTOK_UPLOAD_MODE", "group": "Upload", "label": "Mode upload TikTok", "type": "enum", "options": ["draft", "post"],
     "labels": {"draft": "Privat — Only you (review dulu)", "post": "Langsung posting (publik)"},
     "help": "TikTok Studio web tidak punya tombol draf: mode privat memposting dengan visibilitas 'Only you' — bisa diedit lalu dipublikasikan kapan saja."},
    {"key": "YTDLP_COOKIES", "group": "Upload", "label": "Cookies untuk download (yt-dlp)", "type": "path", "help": "Opsional, untuk video yang butuh login"},
    # --- Lanjutan
    {"key": "ANTHROPIC_EFFORT", "group": "Lanjutan", "label": "Ketelitian Claude", "type": "enum", "options": ["low", "medium", "high", "xhigh", "max"],
     "labels": {"low": "Rendah (cepat)", "medium": "Sedang", "high": "Tinggi", "xhigh": "Sangat tinggi", "max": "Maksimal (paling lama)"}, "help": "Hanya berlaku bila memakai Claude"},
    {"key": "ANTHROPIC_REFUSAL_FALLBACK", "group": "Lanjutan", "label": "Pindah provider bila Claude menolak", "type": "bool"},
    {"key": "CUSTOM_AI_BASE_URL", "group": "Lanjutan", "label": "Custom AI: base URL", "type": "url", "help": "Endpoint kompatibel OpenAI, mis. https://host/v1"},
    {"key": "CUSTOM_AI_API_KEY", "group": "Lanjutan", "label": "Custom AI: API key", "type": "secret"},
    {"key": "CUSTOM_AI_MODEL", "group": "Lanjutan", "label": "Custom AI: nama model", "type": "str"},
    {"key": "OLLAMA_BASE_URL", "group": "Lanjutan", "label": "Alamat Ollama", "type": "url"},
    {"key": "ANTHROPIC_BASE_URL", "group": "Lanjutan", "label": "Alamat API Anthropic", "type": "url", "help": "Biarkan default kecuali memakai proxy"},
    {"key": "GOOGLE_AI_PROJECT_ID", "group": "Lanjutan", "label": "Google project ID (Antigravity)", "type": "str", "help": "Opsional. Default diambil dari client_secret.json"},
]
_BY_KEY = {item["key"]: item for item in SCHEMA}


class SettingsError(ValueError):
    pass


# ----------------------------------------------------------------------------- .env I/O

_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")


def _read_lines() -> List[str]:
    if ENV_PATH.exists():
        return ENV_PATH.read_text(encoding="utf-8").splitlines()
    if EXAMPLE_PATH.exists():
        return EXAMPLE_PATH.read_text(encoding="utf-8").splitlines()
    return []


def _unquote(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\") if value[0] == '"' else inner
    return re.split(r"\s+#", value, maxsplit=1)[0].strip()  # komentar inline


def _quote(value: str) -> str:
    if value == "" or re.fullmatch(r"[A-Za-z0-9_./:@,+\-]*", value):
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def read_env() -> Dict[str, str]:
    values: Dict[str, str] = {}
    for line in _read_lines():
        match = _LINE_RE.match(line)
        if match and not line.lstrip().startswith("#"):
            values[match.group(1)] = _unquote(match.group(2))
    return values


def _write_env(updates: Dict[str, str]) -> None:
    lines = _read_lines()
    pending = dict(updates)
    out: List[str] = []
    for line in lines:
        match = _LINE_RE.match(line)
        if match and not line.lstrip().startswith("#") and match.group(1) in pending:
            key = match.group(1)
            out.append(f"{key}={_quote(pending.pop(key))}")
        else:
            out.append(line)
    if pending:
        if out and out[-1].strip():
            out.append("")
        out.append("# ===== Disimpan dari UI =====")
        out.extend(f"{key}={_quote(value)}" for key, value in pending.items())
    tmp = ENV_PATH.parent / ".env.tmp"
    tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.replace(tmp, ENV_PATH)


# ----------------------------------------------------------------------------- public API

def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 10:
        return "•" * len(value)
    return f"{value[:6]}…{value[-4:]}"


def get_settings() -> Dict:
    """Nilai saat ini untuk UI. Secret hanya {set, masked}."""
    env = read_env()
    values, secrets = {}, {}
    for item in SCHEMA:
        key = item["key"]
        current = getattr(config, key, env.get(key, ""))
        if item["type"] == "secret":
            real = "" if config._is_placeholder(str(current or "")) else str(current or "")
            secrets[key] = {"set": bool(real), "masked": mask(real)}
        elif item["type"] == "bool":
            values[key] = bool(current) if isinstance(current, bool) else str(current).lower() in ("1", "true", "yes")
        else:
            values[key] = "" if current is None else str(current)
    groups: List[str] = []
    for item in SCHEMA:
        if item["group"] not in groups:
            groups.append(item["group"])
    from . import ai_providers, connections
    return {"schema": [_dynamic(item) for item in SCHEMA], "groups": groups, "values": values, "secrets": secrets,
            "models": ai_providers.all_model_options(),
            "connections": [connections.public(c) for c in connections.load()],
            "env_file": str(ENV_PATH), "env_exists": ENV_PATH.exists()}


def _options(key: str) -> Optional[List[str]]:
    """Pilihan enum yang ikut daftar Koneksi API (provider AI & mesin gambar)."""
    from . import ai_providers, connections
    if key == "AI_PROVIDER":
        return ai_providers.all_providers()
    if key == "IMAGE_PROVIDER":
        return list(_BY_KEY[key]["options"]) + [c["name"] for c in connections.load() if c.get("image_models")]
    return None


def _dynamic(item: Dict) -> Dict:
    opts = _options(item["key"])
    if opts is None:
        return item
    from . import connections
    labels = dict(item.get("labels") or {})
    for c in connections.load():
        if c["name"] in opts and c["name"] not in labels:
            labels[c["name"]] = f"{c['name']} (koneksi" + (f", {c.get('image_model')})" if item["key"] == "IMAGE_PROVIDER" else ")")
    return {**item, "options": opts, "labels": labels}


def _validate(key: str, value) -> str:
    item = _BY_KEY.get(key)
    if not item:
        raise SettingsError(f"Pengaturan '{key}' tidak boleh diubah dari UI")
    kind = item["type"]
    if kind == "bool":
        if isinstance(value, str):
            value = value.strip().lower() in ("1", "true", "yes", "on")
        return "1" if value else "0"
    text = "" if value is None else str(value).strip()
    if "\n" in text or "\r" in text or "\x00" in text:
        raise SettingsError(f"{item['label']}: tidak boleh berisi baris baru")
    if len(text) > 2000:
        raise SettingsError(f"{item['label']}: terlalu panjang")
    if kind == "int":
        try:
            number = int(text)
        except ValueError:
            raise SettingsError(f"{item['label']}: harus angka")
        if not item.get("min", number) <= number <= item.get("max", number):
            raise SettingsError(f"{item['label']}: harus {item['min']}–{item['max']}")
        return str(number)
    if kind == "float":
        try:
            number = float(text.replace(",", "."))
        except ValueError:
            raise SettingsError(f"{item['label']}: harus angka")
        if not item.get("min", number) <= number <= item.get("max", number):
            raise SettingsError(f"{item['label']}: harus {item['min']}–{item['max']}")
        return f"{number:g}"
    if kind == "color" and not re.fullmatch(r"#?[0-9A-Fa-f]{6}", text):
        raise SettingsError(f"{item['label']}: format warna #RRGGBB")
    if kind == "enum" and text not in (_options(key) or item["options"]):
        raise SettingsError(f"{item['label']}: pilihan tidak valid ({text})")
    if kind == "url" and text and not re.match(r"^https?://", text):
        raise SettingsError(f"{item['label']}: harus diawali http:// atau https://")
    return text


def _apply_runtime(key: str, raw: str) -> None:
    """Terapkan ke config yang sedang berjalan sesuai tipe aslinya."""
    item = _BY_KEY[key]
    os.environ[key] = raw
    if item["type"] == "bool":
        value = raw == "1"
    elif item["type"] == "int":
        value = int(raw)
    elif item["type"] == "float":
        value = float(raw)
    elif item["type"] in ("url",):
        value = raw.rstrip("/")
    else:
        value = raw
    setattr(config, key, value)


# ----------------------------------------------------------------------------- setelan otomatis

# Format key yang dikenali — key dengan format salah dianggap tidak ada (dan disarankan dihapus).
_KEY_FORMATS = {"GROQ_API_KEY": r"^gsk_\w{20,}$", "OPENAI_API_KEY": r"^sk-[\w-]{20,}$", "ANTHROPIC_API_KEY": r"^sk-ant-[\w-]{20,}$",
                "DEEPSEEK_API_KEY": r"^sk-\w{20,}$", "GEMINI_API_KEY": r"^AIza[\w-]{30,}$", "OPENROUTER_API_KEY": r"^sk-or-[\w-]{20,}$"}
# Suara ElevenLabs berbahasa Indonesia (pria muda, jelas & percaya diri — cocok untuk konten pendek)
ELEVENLABS_ID_VOICE = "q8qwd1jY2jS3AWOBeq25"
# Urutan kualitas LLM (provider, model). OpenAI memakai gpt-4o karena gpt-5.x butuh organisasi terverifikasi.
_LLM_RANK = [("Anthropic", "claude-sonnet-5-5"), ("DeepSeek", "deepseek-flash"), ("OpenAI", "gpt-4o"),
             ("Gemini", "gemini-2.5-flash"), ("Mistral", "mistral-large-latest"), ("Groq", "llama-3.3-70b-versatile"),
             ("OpenRouter", "openrouter/free")]
_PROVIDER_KEY = {"Anthropic": "ANTHROPIC_API_KEY", "DeepSeek": "DEEPSEEK_API_KEY", "OpenAI": "OPENAI_API_KEY", "Gemini": "GEMINI_API_KEY",
                 "Mistral": "MISTRAL_API_KEY", "Groq": "GROQ_API_KEY", "OpenRouter": "OPENROUTER_API_KEY"}


def _real_key(key: str) -> str:
    value = str(getattr(config, key, "") or "").strip()
    return "" if config._is_placeholder(value) else value


def _has_cuda() -> bool:
    import shutil
    import subprocess
    if not shutil.which("nvidia-smi"):
        return False
    try:
        return subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=10).returncode == 0
    except Exception:
        return False


def _openai_models(key: str) -> List[str]:
    try:
        import requests
        r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=15)
        return [m["id"] for m in r.json().get("data", [])] if r.status_code == 200 else []
    except Exception:
        return []


def recommended() -> Dict:
    """Setelan terbaik berdasarkan API key yang benar-benar terpasang. Return {values, clear, notes}."""
    notes: List[str] = []
    clear: List[str] = []
    keys: Dict[str, str] = {}
    for key in {*_PROVIDER_KEY.values(), "ELEVENLABS_API_KEY", "POLLINATIONS_TOKEN"}:
        value = _real_key(key)
        pattern = _KEY_FORMATS.get(key)
        if value and pattern and not re.match(pattern, value):
            clear.append(key)
            notes.append(f"{_BY_KEY[key]['label'] if key in _BY_KEY else key}: format key tidak valid → dihapus")
            value = ""
        keys[key] = value
    has = lambda k: bool(keys.get(k))  # noqa: E731

    v: Dict[str, object] = {}
    from . import connections
    conns = [c for c in connections.load() if c.get("models")]
    llms = [(c["name"], c.get("default_model") or c["models"][0]) for c in conns]
    llms += [(p, m) for p, m in _LLM_RANK if has(_PROVIDER_KEY[p])]
    if llms:
        v["AI_PROVIDER"], v["LLM_MODEL"] = llms[0]
        v["AI_FALLBACK_PROVIDERS"] = ",".join(f"{p}:{m}" for p, m in llms[1:3])
        notes.append(f"AI utama: {llms[0][0]} / {llms[0][1]}" + (f" · cadangan: {', '.join(p for p, _ in llms[1:3])}" if len(llms) > 1 else ""))
    else:
        notes.append("Belum ada API key LLM — klip tetap jalan dengan skor lokal")
    v.update(AI_MOMENT_FINDER=True, AI_CLIP_PACKAGING=True, AI_MAX_CANDIDATES=24)

    openai_models = _openai_models(keys["OPENAI_API_KEY"]) if has("OPENAI_API_KEY") else []
    openai_tts = any(m.startswith(("gpt-4o-mini-tts", "tts-1")) for m in openai_models)
    openai_img = any(m.startswith(("gpt-image", "dall-e")) for m in openai_models)
    if openai_models:
        from . import ai_providers
        ai_providers.save_capabilities("OpenAI", {"tts": openai_tts, "image": openai_img})
    if has("ELEVENLABS_API_KEY"):
        v.update(TTS_PROVIDER="elevenlabs", TTS_VOICE=ELEVENLABS_ID_VOICE, ELEVENLABS_TTS_MODEL="eleven_multilingual_v2")
        notes.append("Suara: ElevenLabs (suara Indonesia 'Pratama', model multilingual v2)")
    elif has("GEMINI_API_KEY"):
        v.update(TTS_PROVIDER="gemini", TTS_VOICE="Kore")
    elif openai_tts:
        v.update(TTS_PROVIDER="openai", TTS_VOICE="nova", OPENAI_TTS_MODEL="gpt-4o-mini-tts")
    else:
        v.update(TTS_PROVIDER="edge", TTS_VOICE="id-ID-ArdiNeural")
        notes.append("Suara: Edge TTS gratis")
    img_conn = next((c for c in connections.load() if c.get("image_models")), None)
    if img_conn:
        v.update(IMAGE_PROVIDER=img_conn["name"], IMAGE_MODEL=img_conn.get("image_model") or img_conn["image_models"][0])
        notes.append(f"Gambar AI: {img_conn['name']} / {v['IMAGE_MODEL']}")
    elif has("GEMINI_API_KEY"):
        v["IMAGE_PROVIDER"] = "gemini"
    elif openai_img:
        v.update(IMAGE_PROVIDER="openai", OPENAI_IMAGE_MODEL="gpt-image-1")
    else:
        v["IMAGE_PROVIDER"] = ""
        notes.append("Gambar AI: Pollinations gratis" + ("" if has("POLLINATIONS_TOKEN") else " (lambat tanpa token — isi Gemini key/Pollinations token agar cepat)"))

    gpu = _has_cuda()
    v.update(WHISPER_MODEL="large-v3-turbo" if gpu else "small", WHISPER_COMPUTE_TYPE="int8",
             USE_NVENC=gpu, PARALLEL_CLIPS=3 if gpu else 2)
    if has("ELEVENLABS_API_KEY"):
        # Scribe: kata lebih lengkap & timestamp pas (subtitle tidak nyangkut); Whisper lokal jadi cadangan
        v.update(WHISPER_DEVICE="elevenlabs", ELEVENLABS_STT_MODEL="scribe_v2")
        notes.append("Transkripsi: ElevenLabs Scribe v2 (paling akurat), cadangan Whisper " + ("GPU" if gpu else "CPU"))
    elif gpu:
        v["WHISPER_DEVICE"] = "auto"
        notes.append("Transkripsi: Whisper large-v3-turbo di GPU NVIDIA")
    else:
        v["WHISPER_DEVICE"] = "groq" if has("GROQ_API_KEY") else "cpu"
        notes.append(f"Tanpa GPU NVIDIA — transkripsi via {v['WHISPER_DEVICE']}")
    if gpu:
        notes.append("Render: GPU NVIDIA (NVENC), 2 klip sekaligus")
    v.update(WHISPER_LANGUAGE="", WHISPER_BEAM_SIZE=5, WHISPER_BATCH_SIZE=16,
             EDIT_STYLE="dinamis", SCENE_SNAP_ENABLED=True, PEAK_THUMBNAIL=True, ENABLE_HOOK_PUNCH=True,
             KEEP_SOURCE_VIDEO=True, ENABLE_PUBLISH_PACKAGE=True)

    cookies = str(getattr(config, "YTDLP_COOKIES", "") or "")
    if cookies and not (config.BASE_DIR / cookies).exists() and not Path(cookies).exists():
        v["YTDLP_COOKIES"] = ""
        notes.append(f"Cookies yt-dlp '{cookies}' tidak ada → dikosongkan")
    return {"values": v, "clear": clear, "notes": notes}


def apply_recommended() -> Dict:
    rec = recommended()
    result = save_settings(rec["values"], rec["clear"])
    from . import ai_providers
    found = ai_providers.detect_all_configured()  # isi dropdown model untuk semua provider yang punya key
    if found:
        rec["notes"].append("Model terdeteksi: " + ", ".join(f"{p} ({n})" for p, n in found.items()))
    return {**result, "models": ai_providers.all_model_options(), "notes": rec["notes"]}


def save_settings(values: Optional[Dict] = None, clear: Optional[List[str]] = None) -> Dict:
    """Validasi lalu simpan ke .env + terapkan langsung.

    values: {KEY: nilai}. Untuk secret, string kosong/None = tidak diubah (pakai `clear` untuk menghapus).
    clear:  daftar KEY secret yang ingin dikosongkan.
    """
    values = dict(values or {})
    updates: Dict[str, str] = {}
    for key, value in values.items():
        item = _BY_KEY.get(key)
        if item and item["type"] == "secret" and (value is None or str(value).strip() == ""):
            continue
        updates[key] = _validate(key, value)
    for key in clear or []:
        item = _BY_KEY.get(key)
        if not item or item["type"] != "secret":
            raise SettingsError(f"'{key}' bukan API key yang bisa dihapus")
        updates[key] = ""
    if not updates:
        return {"saved": [], **get_settings()}
    with _LOCK:
        _write_env(updates)
        for key, raw in updates.items():
            _apply_runtime(key, raw)
    return {"saved": sorted(updates), **get_settings()}
