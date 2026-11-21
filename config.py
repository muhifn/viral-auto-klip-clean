"""
Viral Auto Klip v3 - Configuration
Edit this file to customize scoring, styles, keywords, etc.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _is_placeholder(value: str) -> bool:
    """Nilai contoh dari .env.example (mis. 'gsk...', 'your_..._here') dianggap kosong."""
    v = (value or "").strip().lower()
    return (not v) or v.startswith("your_") or v.endswith("...") or v in {"isi_key_kamu", "changeme", "xxx"}


def _secret(name: str) -> str:
    value = os.getenv(name, "")
    return "" if _is_placeholder(value) else value.strip()

# ==================== PATHS ====================
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)
FONT_DIR = BASE_DIR / "fonts"
FONT_DIR.mkdir(exist_ok=True)

CLIPPING_SOFTWARE_API_KEY = _secret("CLIPPING_SOFTWARE_API_KEY")

# Download a cool font for captions if needed (e.g. from Google Fonts)
# Example: Impact, Montserrat, Poppins, etc. Put .ttf in fonts/
DEFAULT_FONT = "Arial"  # or path to .ttf like str(FONT_DIR / "Montserrat-Bold.ttf")

# ==================== WHISPER ====================
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3-turbo")  # tiny, base, small, medium, large-v3-turbo, large-v3
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")  # auto = coba CUDA kalau terdeteksi, fallback CPU otomatis.
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8 paling stabil untuk RTX 3060 6GB; CPU fallback otomatis int8
WHISPER_CUDA_DEVICE_INDEX = int(os.getenv("WHISPER_CUDA_DEVICE_INDEX", "0"))  # index CUDA, bukan index GPU di Task Manager
WHISPER_GPU_SAFE_VRAM_GB = float(os.getenv("WHISPER_GPU_SAFE_VRAM_GB", "5.5"))
WHISPER_ALLOW_LARGE_ON_GPU = os.getenv("WHISPER_ALLOW_LARGE_ON_GPU", "0").lower() in ("1", "true", "yes")
WHISPER_BEAM_SIZE = int(os.getenv("WHISPER_BEAM_SIZE", "5"))
WHISPER_BATCH_SIZE = int(os.getenv("WHISPER_BATCH_SIZE", "16"))  # hanya dipakai saat CUDA (0 = default library)
# Bahasa video: kosong = deteksi otomatis, "id" = Indonesia, "en" = Inggris, dst.
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "").strip().lower()
# Hint awal untuk tanda baca lebih baik. FIX: hanya dipakai bila WHISPER_LANGUAGE=id
# (dulu dipaksakan ke semua video sehingga bisa mengganggu video bahasa lain).
WHISPER_INITIAL_PROMPT = os.getenv(
    "WHISPER_INITIAL_PROMPT",
    "Berikut adalah transkripsi video bahasa Indonesia dengan tanda baca yang benar.",
)
# Mesin transkripsi cloud: ElevenLabs Scribe (akurasi tinggi, timestamp per kata)
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
GROQ_WHISPER_FALLBACK = os.getenv("GROQ_WHISPER_FALLBACK", "1").lower() in ("1", "true", "yes")
GROQ_WHISPER_AUDIO_BITRATE = os.getenv("GROQ_WHISPER_AUDIO_BITRATE", "64k")

# ==================== YT-DLP / DOWNLOAD ====================
# Optional cookies.txt path for YouTube videos that require login/bot verification.
# Relative paths are resolved from the project root, e.g. YTDLP_COOKIES=cookies.txt
YTDLP_COOKIES = os.getenv("YTDLP_COOKIES", "").strip()
# Kualitas maksimum download sumber: 1080/1440/2160, 0 = tertinggi.
DOWNLOAD_MAX_HEIGHT = int(os.getenv("DOWNLOAD_MAX_HEIGHT", "1080") or "1080")
# Override CQ/CRF encoder. 0 = ikut codebase (CQ 14 untuk file antara, crf-1 untuk final).
ENCODE_CQ = int(os.getenv("ENCODE_CQ", "0") or "0")

# ==================== VIRAL SCORING ====================
MIN_CLIP_DURATION = 15  # seconds
MAX_CLIP_DURATION = 60
IDEAL_CLIP_DURATION = 30

# Viral keywords (Bahasa Indonesia + English) - tambah sesuai niche kamu!
VIRAL_KEYWORDS = {
    "humor": ["lucu", "gokil", "ngakak", "rofl", "haha", "wtf", "shocking", "gila", "aneh", "funny", "joke", "punchline", "kocak", "absurd"],
    "motivasi": ["sukses", "motivasi", "rahasia", "cara", "tips", "how to", "jangan lewatkan", "ubah hidup", "dream", "goal", "inspirasi", "bangkit", "mindset"],
    "shocking": ["tidak percaya", "you won't believe", "rahasia", "terkejut", "plot twist", "ending", "akhirnya", "baru tau", "ternyata", "fakta"],
    "emotional": ["sedih", "menangis", "haru", "bangga", "cinta", "keluarga", "perjuangan", "emotional", "touching", "kehilangan", "takut"],
    "educational": ["tutorial", "cara mudah", "step by step", "belajar", "rahasia", "pro tips", "hacks", "kesalahan", "strategi", "framework"],
    "engagement": ["comment", "like", "share", "tag temen", "kamu setuju?", "pilih mana", "tebak", "quiz", "menurut kamu", "setuju nggak"]
}

HOOK_PATTERNS = [
    "jangan", "stop", "ini alasan", "kenapa", "ternyata", "rahasia",
    "kamu harus", "pernah nggak", "gue kasih tahu", "listen", "watch this",
    "the truth", "here is why", "you need to", "nobody tells you"
]

RETENTION_KEYWORDS = [
    "tapi", "namun", "akhirnya", "terus", "lalu", "ternyata", "masalahnya",
    "plot twist", "bagian paling", "ini yang", "wait", "but", "then", "finally"
]

CTA_KEYWORDS = [
    "follow", "subscribe", "komen", "comment", "share", "save", "simpan",
    "tag", "bagikan", "like", "setuju", "pilih"
]

# Scoring weights — komponen dasar berjumlah 100.
# Skor LLM (bila aktif) TIDAK ditambahkan ke dasar; ia dipakai sebagai rerank
# dengan formula: final = dasar*0.58 + llm*0.42 (lebih jujur & stabil).
SCORING_WEIGHTS = {
    "keyword_match": 25,
    "sentiment_intensity": 20,
    "hook_presence": 15,
    "length_score": 10,
    "visual_interest": 10,  # face close-up, motion
    "retention_curve": 10,
    "shareability": 10,
}
LLM_RERANK_WEIGHT = 0.42  # porsi skor LLM pada reranking akhir (0 = nonaktifkan rerank)

MIN_VIRAL_SCORE = 55  # default threshold

# ==================== LLM / AI SCORING ====================
GROQ_API_KEY = _secret("GROQ_API_KEY")
OPENAI_API_KEY = _secret("OPENAI_API_KEY")
GEMINI_API_KEY = _secret("GEMINI_API_KEY")
OPENROUTER_API_KEY = _secret("OPENROUTER_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Top-tier providers (v4 AI upgrade — semua dipakai lewat core/ai_providers.py)
ANTHROPIC_API_KEY = _secret("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "")  # model gambar untuk mesin gambar dari Koneksi API (v6.6)
# Effort Claude: low | medium | high | xhigh | max (kedalaman berpikir vs biaya/waktu)
ANTHROPIC_EFFORT = os.getenv("ANTHROPIC_EFFORT", "medium").strip().lower()
# Bila Claude menolak (refusal), API otomatis menjalankan ulang di model fallback (server-side)
ANTHROPIC_REFUSAL_FALLBACK = os.getenv("ANTHROPIC_REFUSAL_FALLBACK", "1").lower() in ("1", "true", "yes")
DEEPSEEK_API_KEY = _secret("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MISTRAL_API_KEY = _secret("MISTRAL_API_KEY")
MISTRAL_BASE_URL = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
ELEVENLABS_API_KEY = _secret("ELEVENLABS_API_KEY")
ELEVENLABS_STT_MODEL = os.getenv("ELEVENLABS_STT_MODEL", "scribe_v2")
ELEVENLABS_AUDIO_BITRATE = os.getenv("ELEVENLABS_AUDIO_BITRATE", "64k")

# Custom AI (OpenAI-compatible): bawa base URL + API key sendiri
CUSTOM_AI_BASE_URL = os.getenv("CUSTOM_AI_BASE_URL", "")
CUSTOM_AI_API_KEY = _secret("CUSTOM_AI_API_KEY")
CUSTOM_AI_MODEL = os.getenv("CUSTOM_AI_MODEL", "")

# Antigravity (Google Login) — Gemini via OAuth akun Google, tanpa API key
GOOGLE_AI_TOKEN_FILE = ".google_ai_token.json"  # tersimpan di BASE_DIR (jangan di-commit!)
GOOGLE_AI_SAVED_SECRET = "google_client_secret.json"  # lokasi file yang di-upload lewat UI (di-gitignore)


def _find_google_client_secret() -> str:
    """.env dulu; kalau kosong pakai file hasil upload UI atau client_secret*.json di folder proyek."""
    explicit = os.getenv("GOOGLE_AI_CLIENT_SECRET_FILE", "").strip()
    if explicit:
        return explicit
    saved = BASE_DIR / GOOGLE_AI_SAVED_SECRET
    if saved.exists():
        return str(saved)
    found = sorted(BASE_DIR.glob("client_secret*.json"))
    return str(found[0]) if found else ""


GOOGLE_AI_CLIENT_SECRET_FILE = _find_google_client_secret()
GOOGLE_AI_MODEL = os.getenv("GOOGLE_AI_MODEL", "gemini-2.5-flash")  # default model untuk Antigravity
GOOGLE_AI_PROJECT_ID = os.getenv("GOOGLE_AI_PROJECT_ID", "")  # opsional; default diambil dari client_secret.json

# Fallback berantai bila provider utama gagal/rate-limit. Format: "Groq,Gemini" atau "Anthropic:claude-sonnet-5-5,Groq"
AI_FALLBACK_PROVIDERS = os.getenv("AI_FALLBACK_PROVIDERS", "")

AI_PROVIDER_MODELS = {
    "Groq": [
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-120b",
        "llama-3.1-8b-instant",
    ],
    "OpenAI": [
        "gpt-5.2",
        "gpt-5.1",
        "gpt-5-mini",
        "gpt-4.1",
        "gpt-4o",
    ],
    "Anthropic": [
        "claude-opus-5-5",     # default — paling cerdas di kelas Opus
        "claude-sonnet-5-5",   # cepat & lebih hemat
        "claude-haiku-5-5",    # termurah, untuk volume besar
        "claude-fable-5-2",    # paling kuat (lebih mahal)
    ],
    "Gemini": [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ],
    "Antigravity": [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
    ],
    "DeepSeek": [
        "deepseek-flash",      # default: cepat (±1 menit pilih momen podcast 1 jam)
        "deepseek-v4-pro",     # paling cerdas, tapi model berpikir yang lambat
        "deepseek-chat",
        "deepseek-reasoner",
    ],
    "Mistral": [
        "mistral-large-latest",
        "mistral-medium-latest",
        "mistral-small-latest",
        "ministral-8b-latest",
    ],
    "OpenRouter": [
        "openrouter/free",
    ],
    "Ollama": [
        "qwen2.5:7b",
        "llama3.1:8b",
        "gemma3:4b",
    ],
    "Custom": [],
}

ALL_AI_PROVIDERS = [
    "Groq", "OpenAI", "Anthropic", "Gemini", "Antigravity",
    "DeepSeek", "Mistral", "OpenRouter", "Ollama", "Custom",
]

AI_PROVIDER = os.getenv("AI_PROVIDER", "Groq")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
_PROVIDER_KEY_PRESENT = {
    "Groq": bool(GROQ_API_KEY), "OpenAI": bool(OPENAI_API_KEY), "Anthropic": bool(ANTHROPIC_API_KEY),
    "Gemini": bool(GEMINI_API_KEY), "DeepSeek": bool(DEEPSEEK_API_KEY), "Mistral": bool(MISTRAL_API_KEY),
    "OpenRouter": bool(OPENROUTER_API_KEY), "Custom": bool(CUSTOM_AI_BASE_URL and CUSTOM_AI_API_KEY),
    "Ollama": True, "Antigravity": (BASE_DIR / GOOGLE_AI_TOKEN_FILE).exists(),
}
# FIX: dulu True bila ADA key apa pun walau provider aktif tidak punya key -> AI "aktif" tapi diam-diam tak jalan.
USE_LLM_SCORING = _PROVIDER_KEY_PRESENT.get(AI_PROVIDER, False)
AI_MAX_CANDIDATES = int(os.getenv("AI_MAX_CANDIDATES", "24"))  # cap AI calls per source video

# ==================== AI MOMENT FINDER & PACKAGING (NEW v4) ====================
# AI membaca SELURUH transkrip (bertimestamp) lalu mengusulkan momen terbaik sendiri —
# bukan hanya menilai ulang potongan hasil sliding-window.
AI_UPSCALE = os.getenv("AI_UPSCALE", "1").lower() in ("1", "true", "yes")  # Real-ESRGAN: PyTorch CUDA (tools/models) atau ncnn (tools/realesrgan)
# v6.8: video AI generatif (Content Creator / Story Studio / Motion Graphic)
KLING_API_KEY = _secret("KLING_API_KEY")
KLING_BASE_URL = os.getenv("KLING_BASE_URL", "https://api-singapore.klingai.com")
KLING_VIDEO_MODEL = os.getenv("KLING_VIDEO_MODEL", "kling-3.0-turbo")
GEMINI_VIDEO_MODEL = os.getenv("GEMINI_VIDEO_MODEL", "gemini-omni-1.2-flash")
VIDEO_AI_RESOLUTION = os.getenv("VIDEO_AI_RESOLUTION", "720p")
VIDEO_AI_MAX_SCENES = int(os.getenv("VIDEO_AI_MAX_SCENES", "4"))  # batas adegan yang dihidupkan per video (biaya)
# v6.8: mode Otomatis Analisis AI (isian dikosongkan = AI menentukan)
AUTO_MINUTES_PER_CLIP = float(os.getenv("AUTO_MINUTES_PER_CLIP", "4.5"))  # batas atas ±1 klip per 4,5 menit konten
AUTO_MIN_CLIPS = int(os.getenv("AUTO_MIN_CLIPS", "3"))
AUTO_MAX_CLIPS = int(os.getenv("AUTO_MAX_CLIPS", "30"))
AUTO_MIN_DURATION = int(os.getenv("AUTO_MIN_DURATION", "20"))  # <20 dtk sering tanpa konteks/payoff
AUTO_MAX_DURATION = int(os.getenv("AUTO_MAX_DURATION", "90"))
AUTO_MIN_RUBRIC = float(os.getenv("AUTO_MIN_RUBRIC", "56"))
AUTO_FARM_MIN_RUBRIC = float(os.getenv("AUTO_FARM_MIN_RUBRIC", "46"))  # mode farming: klip "lumayan" ikut diambil
AUTO_FARM_MINUTES_PER_CLIP = float(os.getenv("AUTO_FARM_MINUTES_PER_CLIP", "3"))
AUTO_FARM_MAX_CLIPS = int(os.getenv("AUTO_FARM_MAX_CLIPS", "40"))  # saringan kualitas Editor-AI saat jumlah klip otomatis
# v6.8: upload otomatis ke jam FYP terbaik
TIKTOK_PROFILE = os.getenv("TIKTOK_PROFILE", "")  # @username TikTok — untuk mengukur views 24 jam per jam upload
GLOBAL_HASHTAGS = os.getenv("GLOBAL_HASHTAGS", "")  # mis. "#veruclipper #fyp" — ditambahkan ke SEMUA upload
AUTO_PUBLISH_PER_DAY = int(os.getenv("AUTO_PUBLISH_PER_DAY", "3"))  # maks upload otomatis per platform per hari
AUTO_PUBLISH_MIN_GAP_H = float(os.getenv("AUTO_PUBLISH_MIN_GAP_H", "2.5"))  # jarak minimal antar upload (jam)
VISION_REVIEW = os.getenv("VISION_REVIEW", "1").lower() in ("1", "true", "yes")  # Editor-AI melihat frame (live/gaming)
VISION_PROVIDER = os.getenv("VISION_PROVIDER", "")  # kosong = otomatis (koneksi dengan model Claude/GPT-4o/Gemini)
VISION_MODEL = os.getenv("VISION_MODEL", "")
TRENDS_AUTO_REFRESH = os.getenv("TRENDS_AUTO_REFRESH", "1").lower() in ("1", "true", "yes")  # riset tren otomatis
TRENDS_REFRESH_MIN = int(os.getenv("TRENDS_REFRESH_MIN", "60"))  # interval pembaruan (menit)
AUTO_TEMPO = os.getenv("AUTO_TEMPO", "1").lower() in ("1", "true", "yes")  # percepat halus pembicara lambat
AUTO_TEMPO_TARGET_WPS = float(os.getenv("AUTO_TEMPO_TARGET_WPS", "3.15"))  # kata/detik yang dituju
AUTO_TEMPO_MAX = float(os.getenv("AUTO_TEMPO_MAX", "1.08"))  # batas atas (lebih dari ±1,1× terdengar dipercepat)
AUDIO_SIGNALS = os.getenv("AUDIO_SIGNALS", "1").lower() in ("1", "true", "yes")  # energi/nada/tawa dari suara → skor, AI, punch-in
AI_FACE_RESTORE = os.getenv("AI_FACE_RESTORE", "1").lower() in ("1", "true", "yes")  # GFPGAN v1.4 (tools/models), butuh PyTorch CUDA
AI_FACE_WEIGHT = max(0.0, min(1.0, float(os.getenv("AI_FACE_WEIGHT", "0.6"))))  # 0 = asli, 1 = penuh GFPGAN
AI_REVIEW_PASSES = int(os.getenv("AI_REVIEW_PASSES", "2"))  # penilaian independen per klip; skor dirata-rata
AI_REVIEW_MODEL = os.getenv("AI_REVIEW_MODEL", "")  # kosong = LLM_MODEL; isi model yang lebih kuat bila gateway melayaninya
AI_EDITOR_REVIEW = os.getenv("AI_EDITOR_REVIEW", "1").lower() in ("1", "true", "yes")  # tinjauan kritis tiap klip
REVIEW_MIN_STANDALONE = float(os.getenv("REVIEW_MIN_STANDALONE", "5"))  # klip yang tak bisa dipahami sendiri ditolak
REVIEW_MIN_PAYOFF = float(os.getenv("REVIEW_MIN_PAYOFF", "5"))          # klip tanpa payoff/menggantung ditolak
REVIEW_MIN_SCORE = float(os.getenv("REVIEW_MIN_SCORE", "52"))           # skor rubrik minimum (0-100)
AI_MOMENT_BONUS = float(os.getenv("AI_MOMENT_BONUS", "6"))  # bonus peringkat untuk momen pilihan AI (awal/akhir utuh)
AI_RERANK_WORKERS = int(os.getenv("AI_RERANK_WORKERS", "6"))  # panggilan rerank LLM paralel
AI_MOMENT_FINDER = os.getenv("AI_MOMENT_FINDER", "1").lower() in ("1", "true", "yes")
AI_MOMENT_CHUNK_CHARS = int(os.getenv("AI_MOMENT_CHUNK_CHARS", "24000"))  # ukuran potongan transkrip per panggilan
AI_MOMENT_MAX_CHUNKS = int(os.getenv("AI_MOMENT_MAX_CHUNKS", "30"))       # batas panggilan per video; bila lebih,
# potongan diperbesar (v6.8: dulu potongan sisanya DIBUANG → ±1/3 akhir video 4 jam tidak pernah dibaca AI)
# AI menulis hook, judul, caption upload & hashtag untuk tiap klip final
AI_CLIP_PACKAGING = os.getenv("AI_CLIP_PACKAGING", "1").lower() in ("1", "true", "yes")

VIRAL_PROMPT = """
Kamu adalah expert viral content analyst untuk TikTok, YouTube Shorts, dan Instagram Reels.

Analisis segmen video berikut (transcript + durasi + konteks):
{segment_info}

Berikan:
1. Viral Score: 0-100 (seberapa mungkin jadi viral)
2. Kategori utama: lucu | motivasi | shocking | emotional | educational | hook
3. Alasan singkat (1 kalimat kenapa orang akan share/nonton sampai habis)
4. Saran improvement (opsional)

Aturan scoring:
- Naikkan score hanya jika segmen terasa utuh: ada konteks/setup, inti konflik/poin, dan payoff/ending.
- Turunkan score jika segmen seperti potongan random, mulai di tengah kalimat, ending menggantung tanpa rasa penasaran, atau tidak jelas siapa/apa yang dibahas.
- Untuk podcast/storytelling, segmen 35-60 detik boleh lebih bagus daripada 30 detik jika konteksnya lebih lengkap.
- Jangan pilih hanya karena ada keyword viral; utamakan momen yang benar-benar bisa ditonton ulang/share.

Jawab dalam format JSON ketat:
{{"score": 78, "category": "lucu", "reason": "Punchline dadakan + ekspresi wajah bikin orang ngakak", "suggestion": "Tambah zoom di muka saat punchline"}}
"""

# ==================== FACE & REFRAMING ====================
ENABLE_FACE_DETECTION = True
FACE_DETECTION_CONFIDENCE = 0.5
SMOOTHING_FRAMES = 15  # smooth camera movement
TARGET_ASPECT = (9, 16)  # vertical
OUTPUT_RESOLUTION = (1080, 1920)  # Full HD vertical

# ==================== CAPTIONS ====================
CAPTION_STYLES = {
    # NEW v4: kata yang sedang diucapkan menyala & membesar (gaya OpusClip/Submagic)
    # v4 FIX: ukuran untuk kanvas 1080x1920 — dulu 42–52px (terlalu kecil di HP) dan MarginV 95
    # (zona tombol/caption TikTok). Sekarang 64–80px dan vertical_position ±420px dari bawah.
    # Emoji di caption hanya untuk style "emoji" (font caption umumnya tidak punya glyph berwarna).
    "viral": {
        "font_size": 76,
        "color": (255, 255, 255),
        "stroke_color": (0, 0, 0),
        "stroke_width": 7,
        "position": "center",
        "animation": "active",
        "active_color": (255, 230, 0),
        "uppercase": True,
        "emoji": False,
        "bold": True,
        "vertical_position": 420,
    },
    "modern": {
        "font_size": 70,
        "color": (255, 255, 255),
        "stroke_color": (0, 0, 0),
        "stroke_width": 5,
        "position": "center",
        "animation": "pop",
        "emoji": False,
        "vertical_position": 420,
    },
    "minimal": {
        "font_size": 60,
        "color": (255, 255, 255),
        "stroke_color": (0, 0, 0),
        "stroke_width": 3,
        "position": "bottom",
        "animation": "fade",
        "emoji": False,
        "vertical_position": 380,
    },
    "karaoke": {
        "font_size": 72,
        "color": (255, 215, 0),  # gold = sudah diucapkan
        "stroke_color": (0, 0, 0),
        "stroke_width": 6,
        "position": "center",
        "animation": "karaoke",
        "emoji": False,
        "vertical_position": 420,
    },
    "emoji": {
        "font_size": 68,
        "color": (255, 255, 255),
        "stroke_color": (0, 0, 0),
        "stroke_width": 5,
        "position": "center",
        "animation": "pop",
        "emoji": True,
        "emoji_heavy": True,
        "vertical_position": 420,
    },
    "tiktok_bold": {
        "font_size": 80,
        "color": (255, 255, 255),
        "stroke_color": (0, 0, 0),
        "stroke_width": 8,
        "position": "center",
        "animation": "pop",
        "emoji": False,
        "bold": True,
        "uppercase": True,
        "vertical_position": 420,
    },
    "gradient": {
        "font_size": 70,
        "color": (255, 255, 255),
        "stroke_color": (255, 0, 150),
        "stroke_width": 6,
        "position": "center",
        "animation": "pop",
        "emoji": False,
        "vertical_position": 420,
    },
    "neon": {
        "font_size": 72,
        "color": (0, 255, 255),
        "stroke_color": (255, 0, 255),
        "stroke_width": 7,
        "position": "center",
        "animation": "pop",
        "emoji": False,
        "vertical_position": 420,
    }
}

DEFAULT_CAPTION_STYLE = "modern"
MAX_WORDS_PER_LINE = 8  # for readability on mobile

# Pemetaan kata kunci -> emoji untuk gaya caption emoji/heavy-emoji
EMOJI_KEYWORDS = {
    "😂": ["lucu", "ngakak", "gokil", "kocak", "joke", "punchline", "absurd", "haha"],
    "😱": ["shocking", "plot twist", "ternyata", "gila", "wtf", "baru tau", "tidak percaya"],
    "😢": ["sedih", "menangis", "haru", "kehilangan", "takut"],
    "❤️": ["cinta", "pacar", "keluarga", "bangga", "touching", "mantan"],
    "💰": ["uang", "kaya", "sukses", "cuan", "investasi", "profit", "modal"],
    "💪": ["motivasi", "mindset", "bangkit", "goal", "inspirasi", "perjuangan"],
    "🤯": ["rahasia", "fakta", "you won't believe", "terkejut"],
    "📝": ["tips", "tutorial", "cara", "belajar", "step by step", "hacks"],
    "🎮": ["game", "gaming", "level", "skin", "rank", "boss"],
    "🔥": ["viral", "fyp", "hot", "dahsyat", "hebat"],
}

# ==================== SCENE & EDITING (NEW v3) ====================
SCENE_SNAP_ENABLED = os.getenv("SCENE_SNAP_ENABLED", "1").lower() in ("1", "true", "yes")
SCENE_SNAP_TOLERANCE = float(os.getenv("SCENE_SNAP_TOLERANCE", "1.5"))  # detik
SCENE_DETECT_THRESHOLD = float(os.getenv("SCENE_DETECT_THRESHOLD", "27"))
PEAK_THUMBNAIL = os.getenv("PEAK_THUMBNAIL", "1").lower() in ("1", "true", "yes")  # thumbnail di momen paling "panas", bukan tengah klip
ENABLE_HOOK_PUNCH = os.getenv("ENABLE_HOOK_PUNCH", "1").lower() in ("1", "true", "yes")  # zoom-in punch 0.8 detik pertama
PARALLEL_PROCESSING = os.getenv("PARALLEL_PROCESSING", "1").lower() in ("1", "true", "yes")

# ==================== OUTPUT ====================
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
VIDEO_BITRATE = "5000k"
AUDIO_BITRATE = "192k"
PRESET = os.getenv("X264_PRESET", "slow")  # fallback CPU (tanpa NVENC): slow = kualitas lebih baik
USE_NVENC = os.getenv("USE_NVENC", "1").lower() in ("1", "true", "yes")
NVENC_PRESET = os.getenv("NVENC_PRESET", "p7")  # p7 = kualitas NVENC tertinggi
NVENC_CQ = int(os.getenv("NVENC_CQ", "20"))
KEEP_SOURCE_VIDEO = os.getenv("KEEP_SOURCE_VIDEO", "1").lower() in ("1", "true", "yes")

ADD_WATERMARK = False
WATERMARK_TEXT = "@yourhandle"
WATERMARK_OPACITY = 0.6

ADD_END_SCREEN = True
END_SCREEN_TEXT = os.getenv("END_SCREEN_TEXT", "Follow buat part selanjutnya!")

# ==================== PRO EDITING (NEW v4) ====================
# Preset: minimal (potong + caption) | dinamis (jump cut, zoom, progress bar, grade natural) | maksimal (+ SFX, grade vibrant)
EDIT_STYLE = os.getenv("EDIT_STYLE", "dinamis").strip().lower()
JUMP_CUT_MAX_GAP = float(os.getenv("JUMP_CUT_MAX_GAP", "0.55"))  # jeda > ini (detik) dipotong
PROGRESS_BAR_COLOR = os.getenv("PROGRESS_BAR_COLOR", "#FF3B6B")

# ==================== NEW KLIPERS.PRO FEATURES ====================
ENABLE_AUDIO_ENHANCE = True
ENABLE_BACKGROUND_MUSIC = False
BACKGROUND_MUSIC_PATH = ""  # path to mp3/wav
MUSIC_VOLUME = 0.12
AUTO_DUCK = True

ENABLE_BROLL = True  # Auto add intro bumper (Klipers.pro style)
BROLL_FOLDER = ""  # future: custom B-roll clips

ENABLE_HOOK_OPTIMIZER = True
ENABLE_NICHE_DETECTOR = True

# Platform safe zones (caption positioning)
PLATFORM_SAFE_ZONES = {
    "TikTok": "lower_third",
    "Instagram Reels": "bottom_safe",
    "YouTube Shorts": "center",
    "Semua": "center"
}

# ==================== PUBLISHER (NEW v3) ====================
ENABLE_PUBLISH_PACKAGE = os.getenv("ENABLE_PUBLISH_PACKAGE", "1").lower() in ("1", "true", "yes")
PUBLISH_DIR_NAME = "publish"
YOUTUBE_CLIENT_SECRET_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "")
YOUTUBE_PRIVACY = os.getenv("YOUTUBE_PRIVACY", "public")  # public | unlisted | private
# auto = API bila client_secret tersedia, selain itu browser headless (bila cookies ada).
YOUTUBE_UPLOAD_METHOD = os.getenv("YOUTUBE_UPLOAD_METHOD", "auto").strip().lower()
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "22")  # 22 = People & Blogs
YOUTUBE_OAUTH_TOKEN_FILE = ".yt_upload_token.json"  # tersimpan di BASE_DIR (jangan di-commit!)
CAMPAIGN_DEFAULT_PRESET = os.getenv("CAMPAIGN_DEFAULT_PRESET", "motion-klip-gtavi-split.json")
TIKTOK_UPLOADER_PATH = os.getenv("TIKTOK_UPLOADER_PATH", "")  # opsional, path ke executable tiktok-uploader
TIKTOK_COOKIES_FILE = os.getenv("TIKTOK_COOKIES_FILE", "")    # cookies.txt sesi TikTok untuk tiktok-uploader
# draft = posting privat (Only you, bisa dipublikasikan nanti), post = langsung posting
TIKTOK_UPLOAD_MODE = os.getenv("TIKTOK_UPLOAD_MODE", "draft").strip().lower()

# ==================== STUDIO v6: media AI ====================
# TTS: edge (gratis) | openai | gemini | elevenlabs
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge").strip().lower()
TTS_VOICE = os.getenv("TTS_VOICE", "id-ID-ArdiNeural").strip()
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
ELEVENLABS_TTS_MODEL = os.getenv("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")
# Gambar: kosong = otomatis (Gemini bila ada key, kalau tidak Pollinations) | openai | gemini | pollinations | card
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "").strip()  # bawaan huruf kecil; nama Koneksi API apa adanya
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
# Stok footage gratis & riset
POLLINATIONS_TOKEN = _secret("POLLINATIONS_TOKEN")
PEXELS_API_KEY = _secret("PEXELS_API_KEY")
PIXABAY_API_KEY = _secret("PIXABAY_API_KEY")
YOUTUBE_API_KEY = _secret("YOUTUBE_API_KEY")
# Penjadwal upload: cek antrean tiap N detik
SCHEDULER_INTERVAL = int(os.getenv("SCHEDULER_INTERVAL", "30"))

# ==================== OTHER ====================
MAX_CLIPS_PER_VIDEO = 25
PARALLEL_CLIPS = int(os.getenv("PARALLEL_CLIPS", "3"))  # how many clips process in parallel (memory heavy)
LOG_LEVEL = "INFO"

# ==================== FYP PACK ====================
DEFAULT_HASHTAGS = {
    "humor": ["#fyp", "#viral", "#lucu", "#ngakak", "#shorts"],
    "motivasi": ["#fyp", "#motivasi", "#mindset", "#sukses", "#shorts"],
    "shocking": ["#fyp", "#fakta", "#plotwist", "#viral", "#shorts"],
    "emotional": ["#fyp", "#kisahnyata", "#inspirasi", "#viral", "#shorts"],
    "educational": ["#fyp", "#tips", "#belajar", "#edukasi", "#shorts"],
    "engagement": ["#fyp", "#tanyajawab", "#opini", "#viral", "#shorts"],
    "general": ["#fyp", "#viral", "#shorts", "#reels", "#tiktok"]
}
MAX_HASHTAGS = 6
UPLOAD_CAPTION_MAX_CHARS = 140

PLATFORM_PROFILES = {
    "TikTok": {
        "caption_limit": 150,
        "style": "hooky, direct, comment-driven",
        "cta": "Komen pendapat kamu.",
        "preferred_duration": (18, 42),
        "safe_caption_zone": "middle-lower"
    },
    "Instagram Reels": {
        "caption_limit": 180,
        "style": "clean, relatable, save/share-driven",
        "cta": "Simpan buat nanti.",
        "preferred_duration": (15, 45),
        "safe_caption_zone": "lower"
    },
    "YouTube Shorts": {
        "caption_limit": 100,
        "style": "searchable, curiosity-driven",
        "cta": "Subscribe untuk part berikutnya.",
        "preferred_duration": (20, 58),
        "safe_caption_zone": "middle"
    },
    "Semua": {
        "caption_limit": 140,
        "style": "balanced short-form",
        "cta": "Follow untuk clip berikutnya.",
        "preferred_duration": (18, 50),
        "safe_caption_zone": "middle-lower"
    }
}

FYP_AGENT_CHECKS = [
    "Hook terlihat dalam 2 detik pertama",
    "Caption tidak menutup wajah/subjek utama",
    "Durasi cukup padat untuk ditonton ulang",
    "Ada alasan untuk komentar, share, atau save",
    "Hashtag tidak terlalu banyak dan tetap relevan"
]

# Niche-specific (example for gaming/podcast - uncomment & customize)
# GAMING_MODE = True
# PODCAST_MODE = False
