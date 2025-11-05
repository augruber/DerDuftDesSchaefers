import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from typing import Optional
from urllib.parse import urlparse

import qrcode
import requests

import unicodedata
import re

# =========================
# Config
# =========================
CSV_FILENAME = "QR-Code-Liste.csv"    # expects semicolon-delimited with columns: title;artist;url
CSV_HAS_HEADER = True                  # set False if your CSV has no header row
CSV_DELIMITER = ";"                    # change if needed
OUTPUT_PREFIX = "QR-Code-"
DEFAULT_MARKET = os.getenv("SPOTIFY_MARKET", "US")  # market for Spotify search

# Optional Spotify credentials (Client Credentials Flow)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "930bfca7869e46d2aa08be56319ff72d")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "2de710e9c69a4c20ac44010c3627216b")

# Base URL of your redirect service (GitHub Pages)
# Example: "https://yourname.github.io/qr-redirect/"
REDIRECT_BASE_URL = os.getenv("REDIRECT_BASE_URL", "https://redirect.der-duft-des-schaefers.ch")

# Name of the CSV that maps slug -> target URL (for GitHub Pages redirect script)
REDIRECT_CSV_FILENAME = "links.csv"


# =========================
# Helpers
# =========================
def make_timestamped_folder_name(prefix=OUTPUT_PREFIX):
    now = datetime.now()
    return f"{prefix}{now.strftime('Datum_%d-%m-%Y_Zeit_%H-%M-%S')}"


def safe_filename(name: str) -> str:
    return (
        name.replace(" ", "_")
        .replace("/", "-")
        .replace("\\", "-")
        .replace(":", "-")
        .replace("?", "")
        .replace("*", "")
        .replace('"', "")
        .replace("<", "")
        .replace(">", "")
        .replace("|", "")
    )


def load_csv(filename):
    rows = []
    with open(filename, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=CSV_DELIMITER)
        if CSV_HAS_HEADER:
            next(reader, None)
        for row in reader:
            # normalize to [title, artist, url?]
            title = (row[0] or "").strip() if len(row) > 0 else ""
            artist = (row[1] or "").strip() if len(row) > 1 else ""
            url = (row[2] or "").strip() if len(row) > 2 else ""
            if not title and not artist and not url:
                continue
            rows.append([title, artist, url])
    return rows



def slugify(text: str) -> str:
    """
    Turn arbitrary text into a URL-safe, human-readable slug.
    E.g. "Ärger / Spaß" -> "arger-spass"
    """
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "link"


def make_unique_slug(base: str, existing: set) -> str:
    """
    Ensure slugs are unique by adding -2, -3, ... if needed.
    """
    slug = base or "link"
    if slug not in existing:
        existing.add(slug)
        return slug

    index = 2
    while f"{slug}-{index}" in existing:
        index += 1
    unique = f"{slug}-{index}"
    existing.add(unique)
    return unique


def make_redirect_url(slug: str) -> str:
    """
    Build the URL that goes into the QR code:
    <REDIRECT_BASE_URL>/?id=<slug>
    """
    base = REDIRECT_BASE_URL.rstrip("/")
    return f"{base}/?id={quote_plus(slug)}"

# =========================
# Spotify Search
# =========================
def get_spotify_token(client_id: str, client_secret: str) -> Optional[str]:
    """
    Client Credentials Flow token.
    """
    try:
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
        else:
            print(f"⚠️ Spotify auth failed: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        print(f"⚠️ Spotify auth error: {e}")
        return None


def search_spotify_track(title: str, artist: str, token: str, market: str = DEFAULT_MARKET) -> Optional[str]:
    """
    Returns the first Spotify track URL if found, else None.
    Prints a clear message if not found.
    """
    parts = []
    if title:
        parts.append(f'track:"{title}"')
    if artist:
        parts.append(f'artist:"{artist}"')
    q = " ".join(parts) if parts else title

    url = f"https://api.spotify.com/v1/search?q={quote_plus(q)}&type=track&limit=1&market={market}"

    try:
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        if resp.status_code == 200:
            items = resp.json().get("tracks", {}).get("items", [])
            if items:
                return items[0]["external_urls"]["spotify"]
            else:
                print(f"❌ Not found on Spotify: '{title}' by '{artist}' (query: {q})")
                return None

        elif resp.status_code == 429:
            # rate limit → retry after
            retry_after = int(resp.headers.get("Retry-After", "2"))
            print(f"⚠️ Spotify rate-limited, waiting {retry_after}s …")
            time.sleep(retry_after + 1)
            return search_spotify_track(title, artist, token, market)

        else:
            print(f"⚠️ Spotify API error {resp.status_code}: {resp.text[:200]} for '{title}' by '{artist}'")
            return None

    except Exception as e:
        print(f"⚠️ Spotify search exception for '{title}' by '{artist}': {e}")
        return None

# =========================
# Apple Music (iTunes Search API)
# =========================
def search_apple_music_track(title: str, artist: str, country: str = "US") -> Optional[str]:
    """
    Uses the public iTunes Search API (no auth).
    Returns a trackViewUrl which typically redirects to Apple Music.
    """
    term_parts = [title, artist]
    term = " ".join([p for p in term_parts if p]).strip()
    if not term:
        return None

    # iTunes Search API
    url = f"https://itunes.apple.com/search?term={quote_plus(term)}&entity=song&limit=1&country={country}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                return results[0].get("trackViewUrl") or results[0].get("collectionViewUrl")
            return None
        else:
            print(f"⚠️ Apple Music search error {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"⚠️ Apple Music search exception: {e}")
        return None


def platform_from_url(url: str) -> Optional[str]:
    """
    Returns one of: 'Spotify', 'Apple Music', 'Soundcloud', 'Youtube'
    or None if it can't confidently classify.
    """
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:
        return None

    # strip common subdomains for easier matching
    for prefix in ("www.", "m."):
        if netloc.startswith(prefix):
            netloc = netloc[len(prefix):]

    if netloc.endswith("spotify.com"):
        return "Spotify"

    # Apple Music can be music.apple.com, sometimes itunes.apple.com
    if netloc.endswith("apple.com") or netloc.endswith("itunes.apple.com"):
        return "Apple Music"

    if netloc.endswith("soundcloud.com"):
        return "Soundcloud"

    if netloc.endswith("youtube.com") or netloc.endswith("youtu.be"):
        return "Youtube"

    return None

# =========================
# QR Code
# =========================
def save_qr_png(qr_url: str, song: str, artist: str, folder: Path, index: int, target_url: Optional[str] = None) -> str:
    """
    Save a QR code PNG that encodes qr_url.
    target_url (if provided) is used only to detect platform for the filename.
    """
    os.makedirs(folder, exist_ok=True)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Identify the platform for suffix (based on the final music URL, not the redirect URL)
    platform = platform_from_url(target_url)
    base = f"{song}_{artist}".strip("_") if (song or artist) else "link"
    if platform:
        base = f"{base}_{platform}"

    # Add index prefix with leading zeros
    prefix = f"{index:03d}_"  # e.g. 001_
    filename = safe_filename(prefix + base + ".png")

    filepath = folder / filename
    img.save(filepath)
    return str(filepath)


# =========================
# Main
# =========================
def resolve_link(song: str, artist: str, existing_url: Optional[str], spotify_token: Optional[str]) -> tuple[Optional[str], str]:
    """
    Returns (final_url, source_label)
    """
    # 1) Use provided URL if present
    if existing_url:
        return existing_url, "csv"

    # 2) Try Spotify if we have credentials
    if spotify_token:
        sp_url = search_spotify_track(song, artist, spotify_token)
        if sp_url:
            return sp_url, "spotify"

    # 3) Fall back to Apple Music
    am_url = search_apple_music_track(song, artist)
    if am_url:
        return am_url, "apple"

    return None, "none"

if __name__ == "__main__":
    # Prepare output
    output_folder = Path(os.path.dirname(os.path.abspath(__file__))) / make_timestamped_folder_name()
    os.makedirs(output_folder, exist_ok=True)
    print(f"📁 Output folder: {output_folder}")

    # Load CSV
    data = load_csv(CSV_FILENAME)
    if not data:
        print("No rows found in CSV. Exiting.")
        sys.exit(0)

    # Get Spotify token if possible
    spotify_token = None
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        spotify_token = get_spotify_token(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
        if spotify_token:
            print("🔑 Spotify token acquired.")
        else:
            print("⚠️ Could not acquire Spotify token; will fall back to Apple Music for lookups.")

    # For building the slug->URL CSV
    redirect_rows: list[tuple[str, str]] = []
    used_slugs: set = set()

    # Process rows
    for i, row in enumerate(data, start=1):
        song, artist, url = row
        final_url, source = resolve_link(song, artist, url, spotify_token)

        if not final_url:
            print(f"❌ No link found for '{song}' by '{artist}'. Skipping.")
            continue

        # Build slug and redirect URL
        base_slug_text = song or artist or "track"
        base_slug = slugify(f"{song}-{artist}") if (song or artist) else slugify(base_slug_text)
        slug = make_unique_slug(base_slug, used_slugs)
        redirect_url = make_redirect_url(slug)

        # Save QR for the redirect URL
        saved_path = save_qr_png(redirect_url, song, artist, output_folder, i, target_url=final_url)

        # Store mapping for redirect CSV: slug -> final target URL
        redirect_rows.append((slug, final_url))

        print(f"✅ {i:03d}. {song} — {artist} | {source.upper()} → {final_url}")
        print(f"   Slug: {slug}")
        print(f"   Redirect URL (QR contents): {redirect_url}")
        print(f"   QR saved at: {saved_path}")

    # Write the redirect CSV (slug -> final URL) for GitHub Pages
    if redirect_rows:
        redirect_csv_path = output_folder / REDIRECT_CSV_FILENAME
        with open(redirect_csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)  # comma-delimited: slug,url
            writer.writerow(["slug", "url"])
            for slug, target_url in redirect_rows:
                writer.writerow([slug, target_url])

        print(f"🔗 Redirect mapping CSV written to: {redirect_csv_path}")
    else:
        print("No redirects generated; nothing to write to redirect CSV.")