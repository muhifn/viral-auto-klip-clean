#!/usr/bin/env python3
"""Upload ke YouTube lewat browser (Playwright, **selalu headless**).

Kenapa browser, bukan API: kuota YouTube Data API hanya ~10.000 unit/hari dan
satu upload = 1.600 unit (≈6 upload/hari). Browser tidak memakai kuota itu.

Aturan penting (permintaan user): **tidak boleh ada popup/jendela browser**.
Semua jalan headless. Jadi:
    - `headless=True` tidak bisa dimatikan lewat UI
    - tidak ada login interaktif; sesi datang dari cookies yang di-paste di
      Pengaturan (lihat `save_cookies`)
    - kalau cookies kedaluwarsa: kembalikan error yang jelas, JANGAN buka jendela

Cookie disimpan di `data/youtube/cookies.json` (data/ gitignored).
Format yang diterima: JSON (list Playwright / export extension) atau Netscape
cookies.txt.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

import config
from .utils import trim_caption

COOKIE_DIR = config.BASE_DIR / "data" / "youtube"
COOKIE_FILE = COOKIE_DIR / "cookies.json"

TITLE_SELECTOR = (
    '#textbox[placeholder*="title" i], #textbox[placeholder*="judul" i], '
    '#textbox[aria-label*="title" i], #textbox[aria-label*="judul" i], '
    '#textbox[aria-label*="Tambahkan judul" i]'
)
DESCRIPTION_SELECTOR = (
    '#textbox[placeholder*="description" i], #textbox[placeholder*="deskripsi" i], '
    '#textbox[aria-label*="description" i], #textbox[aria-label*="deskripsi" i], '
    '#textbox[aria-label*="Beri tahu penonton" i]'
)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

PRIVACY_MAP = {"public": "PUBLIC", "unlisted": "UNLISTED", "private": "PRIVATE"}


class YouTubeUploadError(ValueError):
    """Upload gagal — pesan sudah ramah untuk ditampilkan di UI."""


# ==================== Cookie management ====================
def _norm_cookie(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Satu cookie → format Playwright, atau None kalau tidak bisa dipakai."""
    name = str(item.get("name") or "").strip()
    value = item.get("value")
    domain = str(item.get("domain") or "").strip()
    if not name or value in (None, ""):
        return None
    if not domain:
        return None
    path = str(item.get("path") or "/")
    expires = item.get("expires", item.get("expirationDate"))
    try:
        expires = float(expires) if expires not in (None, "", -1) else -1
    except (TypeError, ValueError):
        expires = -1
    if expires != -1 and expires < time.time():
        return None  # cookie kedaluwarsa: jangan dikirim
    cookie: Dict[str, Any] = {
        "name": name, "value": str(value), "domain": domain, "path": path,
        "expires": expires, "httpOnly": bool(item.get("httpOnly", False)),
        "secure": bool(item.get("secure", True)),
    }
    same_site = item.get("sameSite")
    if same_site in ("Strict", "Lax", "None"):
        cookie["sameSite"] = same_site
    return cookie


def parse_cookies(raw: str) -> List[Dict[str, Any]]:
    """Terima JSON atau Netscape cookies.txt, kembalikan cookie siap Playwright."""
    text = (raw or "").strip()
    if not text:
        raise YouTubeUploadError("Isi cookies masih kosong")

    # ---- JSON
    if text[0] in "[{":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise YouTubeUploadError(f"JSON cookies tidak valid: {exc}") from exc
        items = data if isinstance(data, list) else data.get("cookies") or []
        cookies = [c for c in (_norm_cookie(item) for item in items if isinstance(item, dict)) if c]
        if not cookies:
            raise YouTubeUploadError("Tidak ada cookie YouTube yang valid di JSON itu")
        return cookies

    # ---- Netscape cookies.txt
    cookies: List[Dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _flag, path, secure, expires, name, value = parts[:7]
        if "youtube" not in domain and "google" not in domain:
            continue
        cookie = _norm_cookie({
            "name": name, "value": value, "domain": domain, "path": path,
            "secure": secure.upper() == "TRUE", "expires": expires,
            "httpOnly": False,
        })
        if cookie:
            cookies.append(cookie)
    if not cookies:
        raise YouTubeUploadError("Tidak ada cookie youtube.com/google.com di file itu")
    return cookies


def save_cookies(raw: str) -> Dict[str, Any]:
    """Validasi lalu simpan cookies. Return ringkasan (tanpa isi cookie)."""
    cookies = parse_cookies(raw)
    COOKIE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"saved_at": time.time(), "cookies": cookies}
    COOKIE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        COOKIE_FILE.chmod(0o600)
    except OSError:
        pass
    return cookie_status()


def load_cookies() -> List[Dict[str, Any]]:
    if not COOKIE_FILE.is_file():
        return []
    try:
        payload = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = payload.get("cookies") if isinstance(payload, dict) else payload
    return [c for c in (_norm_cookie(i) for i in items or [] if isinstance(i, dict)) if c]


def cookie_status() -> Dict[str, Any]:
    """Ringkasan untuk UI — TIDAK pernah mengembalikan nilai cookie."""
    cookies = load_cookies()
    saved_at = None
    if COOKIE_FILE.is_file():
        try:
            saved_at = json.loads(COOKIE_FILE.read_text(encoding="utf-8")).get("saved_at")
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
    soonest = min((c["expires"] for c in cookies if c.get("expires", -1) > 0), default=None)
    return {
        "configured": bool(cookies),
        "count": len(cookies),
        "saved_at": saved_at,
        "expires_at": soonest,
        "path": str(COOKIE_FILE),
    }


def clear_cookies() -> Dict[str, Any]:
    try:
        COOKIE_FILE.unlink(missing_ok=True)
    except OSError as exc:
        raise YouTubeUploadError(f"Tidak bisa menghapus cookies: {exc}") from exc
    return cookie_status()


# ==================== Upload ====================
def _launch(p):
    """Chromium headless; Edge kalau tersedia. Tidak pernah headless=False."""
    args = ["--disable-blink-features=AutomationControlled",
            "--no-first-run", "--no-default-browser-check",
            "--disable-notifications", "--mute-audio"]
    try:
        return p.chromium.launch(channel="msedge", headless=True, args=args)
    except Exception:
        return p.chromium.launch(headless=True, args=args)


def _set_text(page, selector: str, text: str, wait: int = 60_000) -> None:
    box = page.locator(selector).first
    box.wait_for(state="visible", timeout=wait)
    box.click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.wait_for_timeout(200)
    page.keyboard.insert_text(text)
    page.wait_for_timeout(300)


def upload_video(video: Path | str, *, title: str, description: str = "",
                 tags: Optional[List[str]] = None, privacy: str = "private",
                 timeout: int = 300,
                 progress=None) -> Dict[str, Any]:
    """Upload satu video ke YouTube Studio (headless). Return dict hasil.

    `progress(stage: str, pct: int, message: str)` opsional untuk job log.
    Tidak pernah membuka jendela browser dan tidak pernah meminta input.
    """
    def say(stage: str, pct: int, message: str) -> None:
        logger.info(f"[yt-browser] {message}")
        if progress:
            try:
                progress(stage, pct, message)
            except Exception:  # noqa: BLE001
                pass

    video = Path(video).resolve()
    if not video.is_file():
        raise YouTubeUploadError(f"File video tidak ditemukan: {video.name}")

    cookies = load_cookies()
    if not cookies:
        raise YouTubeUploadError(
            "Cookies YouTube belum diatur. Buka Pengaturan → YouTube, lalu tempel cookies."
        )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise YouTubeUploadError(
            "Playwright belum terpasang: pip install playwright && playwright install chromium"
        ) from exc

    privacy = PRIVACY_MAP.get(str(privacy).lower(), "PRIVATE")
    deadline = time.monotonic() + timeout
    say("Upload", 5, f"Membuka YouTube Studio (headless) untuk {video.name}…")

    with sync_playwright() as p:
        browser = _launch(p)
        try:
            context = browser.new_context(user_agent=UA)
            context.add_cookies(cookies)
            page = context.new_page()
            page.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=60_000)
            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
            except Exception:  # noqa: BLE001 - networkidle sering tidak tercapai
                pass
            page.wait_for_timeout(3000)

            if "accounts.google.com" in page.url:
                raise YouTubeUploadError(
                    "Sesi YouTube kedaluwarsa. Perbarui cookies di Pengaturan → YouTube."
                )

            # Buka dialog upload
            file_input = None
            for attempt in range(1, 4):
                say("Upload", 10 + attempt * 5, f"Membuka dialog upload (percobaan {attempt})…")
                btn = page.locator('#upload-button, button:has-text("Upload video"), [aria-label*="Upload" i]').first
                if btn.is_visible(timeout=4000):
                    btn.click()
                else:
                    create = page.locator('#create-icon, button:has-text("Buat"), button:has-text("Create")').first
                    if create.is_visible(timeout=4000):
                        create.click()
                        page.wait_for_timeout(800)
                        page.locator('tp-yt-paper-item:has-text("Upload"), [test-id="upload-action"]').first.click()
                try:
                    candidate = page.locator('input[type="file"]')
                    candidate.wait_for(state="attached", timeout=10_000)
                    file_input = candidate
                    break
                except Exception:  # noqa: BLE001
                    page.wait_for_timeout(2000)
            if file_input is None:
                raise YouTubeUploadError("Dialog upload tidak terbuka setelah 3 percobaan")

            say("Upload", 30, "Memilih file & menunggu form detail…")
            file_input.set_input_files(str(video))
            _set_text(page, TITLE_SELECTOR, title[:100])
            if description:
                try:
                    page.locator('button:has-text("Tampilkan lainnya"), button:has-text("Show more")').first.click(timeout=3000)
                    page.wait_for_timeout(500)
                except Exception:  # noqa: BLE001
                    pass
                _set_text(page, DESCRIPTION_SELECTOR, trim_caption(description, 4900), wait=20_000)
            if tags:
                try:
                    _set_text(page, '#textbox[aria-label*="tag" i], #textbox[placeholder*="tag" i]',
                              ", ".join(tags)[:500], wait=10_000)
                except Exception:  # noqa: BLE001 - tag opsional
                    pass

            # YouTube mewajibkan jawaban "Dibuat untuk Anak-Anak?" sebelum Next aktif.
            # Sama dengan API (selfDeclaredMadeForKids=False): bukan untuk anak-anak.
            say("Upload", 55, "Menjawab 'Dibuat untuk Anak-Anak?' (Tidak)…")
            try:
                mfk = page.locator('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]').first
                if mfk.count():
                    mfk.evaluate("el => el.click()")
                else:
                    page.evaluate(
                        """() => {
                            const els = Array.from(document.querySelectorAll('tp-yt-paper-radio-button'));
                            const el = els.find(e => /tidak, video ini tidak dibuat untuk anak-anak|no,? it.s not made for kids/i.test((e.innerText || '').trim()));
                            if (el) { el.click(); return true; }
                            return false;
                        }""")
                page.wait_for_timeout(600)
            except Exception:  # noqa: BLE001 - pertanyaan opsional bila UI berubah
                pass

            # Wizard: klik Next sampai halaman visibility
            for step in range(3):
                if time.monotonic() > deadline:
                    raise YouTubeUploadError("Upload melewati batas waktu")
                nxt = page.locator("#next-button").first
                try:
                    nxt.wait_for(state="attached", timeout=10_000)
                    page.wait_for_function(
                        """() => { const n = document.querySelector('#next-button');
                                   return n && !n.hasAttribute('disabled'); }""",
                        timeout=600_000)
                    nxt.evaluate("el => el.click()")
                    page.wait_for_timeout(1200)
                except Exception:  # noqa: BLE001
                    break

            say("Upload", 65, f"Mengatur visibilitas: {privacy.lower()}…")
            try:
                page.locator('tp-yt-paper-radio-button[name="PUBLIC"]').first.wait_for(state="attached", timeout=15_000)
            except Exception:  # noqa: BLE001
                pass
            radio = page.locator(f'tp-yt-paper-radio-button[name="{privacy}"]').first
            if radio.count():
                try:
                    radio.click(timeout=5000)
                except Exception:  # noqa: BLE001
                    radio.evaluate("el => el.click()")

            say("Upload", 75, "Menunggu proses selesai & menekan Publish…")
            page.wait_for_function(
                """() => { const d = document.querySelector('#done-button');
                           return d && !d.hasAttribute('disabled') && d.offsetParent !== null; }""",
                timeout=1_800_000)
            page.locator("#done-button").first.evaluate("el => el.click()")
            page.wait_for_timeout(6000)

            # Ambil link video dari dialog konfirmasi
            link = None
            for _ in range(20):
                try:
                    href = page.locator('a[href*="youtu.be/"], a[href*="youtube.com/watch"]').first.get_attribute("href", timeout=2000)
                    if href:
                        link = href
                        break
                except Exception:  # noqa: BLE001
                    pass
                page.wait_for_timeout(1000)

            say("Upload", 100, "Upload selesai")
            return {"ok": True, "url": link, "privacy": privacy.lower(),
                    "title": title, "file": str(video)}
        except YouTubeUploadError:
            raise
        except Exception as exc:  # noqa: BLE001 - pesan Playwright panjang, ringkas
            msg = str(exc).splitlines()[0][:300]
            raise YouTubeUploadError(f"Upload browser gagal: {msg}") from exc
        finally:
            try:
                browser.close()
            except Exception:  # noqa: BLE001
                pass


def test_session() -> Dict[str, Any]:
    """Cek cookies masih valid tanpa upload apa pun. Headless, tanpa popup."""
    cookies = load_cookies()
    if not cookies:
        return {"ok": False, "error": "Cookies belum diatur"}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"ok": False, "error": "Playwright belum terpasang"}
    with sync_playwright() as p:
        browser = _launch(p)
        try:
            context = browser.new_context(user_agent=UA)
            context.add_cookies(cookies)
            page = context.new_page()
            page.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=45_000)
            page.wait_for_timeout(3000)
            if "accounts.google.com" in page.url:
                return {"ok": False, "error": "Cookies kedaluwarsa — perbarui di Pengaturan"}
            channel = ""
            try:
                channel = page.locator("ytcp-account-name, #account-name").first.inner_text(timeout=3000).strip()
            except Exception:  # noqa: BLE001
                pass
            return {"ok": True, "channel": channel}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc).splitlines()[0][:200]}
        finally:
            try:
                browser.close()
            except Exception:  # noqa: BLE001
                pass


__all__ = [
    "YouTubeUploadError", "COOKIE_FILE", "parse_cookies", "save_cookies",
    "load_cookies", "cookie_status", "clear_cookies", "upload_video", "test_session",
]
