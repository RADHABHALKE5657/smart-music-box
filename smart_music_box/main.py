import argparse
import json
import os
import random
import re
import urllib.parse
import urllib.request
import webbrowser
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional

HISTORY_PATH = Path(__file__).parent / "data" / "history.json"
MAX_RECENT = 8

MOODS = ["sad", "happy", "romantic", "stressed", "neutral"]
PLATFORMS = ["youtube", "spotify"]

# Query intent is mood-based (not fixed artist names).
MOOD_QUERIES = {
    "sad": ["sad hindi songs", "emotional hindi songs", "heartbreak hindi songs"],
    "romantic": ["romantic hindi songs", "love hindi songs", "soft romantic hindi songs"],
    "stressed": ["calm hindi songs", "soothing hindi songs", "relaxing hindi indie songs"],
    "happy": ["happy hindi songs", "upbeat hindi songs", "feel good bollywood songs"],
    "neutral": ["chill hindi songs", "soft hindi indie songs", "easy listening hindi songs"],
}

MOOD_KEYWORDS = {
    "sad": {
        "sad", "cry", "hurt", "broken", "lonely", "miss", "pain", "upset", "heartbroken",
        "dukhi", "udaas", "rona", "toot", "thak", "akela", "numb",
    },
    "romantic": {
        "love", "romantic", "kiss", "hug", "date", "cuddle", "beautiful", "jaan", "baby",
        "pyaar", "mohabbat", "ishq", "yaad", "tum", "saath", "dilbar",
    },
    "stressed": {
        "stress", "anxious", "anxiety", "panic", "pressure", "deadline", "tired", "exhausted", "overwhelmed",
        "tension", "ghabra", "pareshan", "load", "kaam", "burnout",
    },
    "happy": {
        "happy", "excited", "joy", "great", "awesome", "fun", "party", "smile", "good news",
        "khush", "mast", "badiya", "maza", "celebrate", "yay",
    },
}

_MISSING_OPTIONAL_MODULES = set()


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def detect_mood_from_text(user_text: str) -> str:
    text = normalize(user_text)
    if not text:
        return "neutral"

    scores = {"sad": 0, "happy": 0, "romantic": 0, "stressed": 0}
    for mood, words in MOOD_KEYWORDS.items():
        for word in words:
            if word in text:
                scores[mood] += 1

    top_mood = max(scores, key=scores.get)
    if scores[top_mood] == 0:
        return "neutral"
    return top_mood


def llm_generate_message(name: str, mood: str, user_text: str = "") -> tuple[Optional[str], Optional[str]]:
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        return None, "HF_TOKEN missing"
    hf_model = os.environ.get("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")

    prompt = (
        "You are a loving girlfriend writing one fresh personal message.\n"
        "Rules:\n"
        "- Write only message text, 1 to 3 lines\n"
        "- Tone: intimate, warm, natural, light Hinglish allowed\n"
        "- Do not include links, commands, code, JSON, or quotes\n"
        f"- Boyfriend name: {name}\n"
        f"- Mood: {mood}\n"
        f"- User context: {user_text or 'N/A'}\n"
        "Generate now."
    )

    try:
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 120,
                "temperature": 1.0,
                "return_full_text": False,
            },
        }
        req = urllib.request.Request(
            url=f"https://api-inference.huggingface.co/models/{hf_model}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {hf_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")

        result = json.loads(raw)
        if isinstance(result, dict) and result.get("error"):
            return None, f"HF API error: {result.get('error')}"
        text = ""
        if isinstance(result, list) and result:
            text = str(result[0].get("generated_text", "")).strip()
        elif isinstance(result, dict) and "generated_text" in result:
            text = str(result.get("generated_text", "")).strip()

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        message = "\n".join(lines[:3]).strip()
        if not message:
            return None, "HF returned empty message"

        blocked = ("http://", "https://", "python ", "search_query=", "{", "}")
        low = message.lower()
        if any(b in low for b in blocked):
            return None, "HF message failed safety checks"
        return message, None
    except Exception as exc:
        return None, f"HF request failed: {exc}"


def fallback_message(name: str, mood: str) -> str:
    dynamic_bits = [
        "I am thinking of you right now.",
        "Kaash main abhi tumhare paas hoti.",
        "Bas ek tight hug bhej rahi hoon.",
        "Take a slow breath with me.",
    ]
    starter = f"{name},"
    mood_lines = {
        "sad": [
           "mujhe pata hai tum thoda low feel kar rahe ho.",
           "kaash main abhi tumhare paas hoti… sab thoda easy lagta.",
           "tum akele nahi ho… main hamesha yahin hoon ❤️",
           "thoda sa time do khud ko… sab theek ho jayega.",
           "bas thoda sa smile karo… mujhe achcha lagega.",
           "tum itna feel karte ho… isi liye tum special ho."
        ],
        "happy": [
            "aaj tumhari vibe bohot achchi lag rahi hai.",
            "tum khush hote ho na… toh sab perfect lagta hai.",
            "aise hi smile karte raho… meri duniya bright ho jaati hai.",
            "tumhari khushi contagious hai 😄",
            "aaj ka din tumhari wajah se aur bhi better lag raha hai.",
            "bas aise hi haste rehna… mujhe bahut pasand hai."

        ],
        "romantic": [
            "tum mere favorite thought ho aaj.",
            "tum ho toh sab kuch thoda sa special lagta hai.",
            "kabhi kabhi bas tumhare baare mein soch ke smile aa jaati hai.",
            "tum meri har choti si khushi ka reason ho.",
            "tumhare bina sab incomplete lagta hai.",
            "bas tum… aur thoda sa music… perfect combo ❤️"
        ],
        "stressed": [
            "aaj ka pressure main samajh sakti hoon.",
            "thoda sa break le lo… sab manage ho jayega.",
            "itna stress mat lo… tum already enough ho.",
            "deep breath lo… main yahin hoon.",
            "sab kuch ek din mein perfect nahi hota… it's okay.",
            "tum handle kar loge… mujhe tum par full trust hai."
        ],
        "neutral": [
            "thoda sa music, thoda sa hum.",
            "aaj bas chill karte hain… bina kisi tension ke.",
            "kabhi kabhi kuch feel na karna bhi theek hota hai.",
            "bas relax karo… main yahin hoon.",
            "simple moments bhi special hote hain.",
            "aaj ka vibe soft aur calm rakhenge."

        ],
    }
    mood_line = random.choice(mood_lines[mood])
    return f"{starter} {mood_line}\n{random.choice(dynamic_bits)}"


def load_history() -> dict:
    if not HISTORY_PATH.exists():
        return {m: [] for m in MOODS}
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid history structure")
        for mood in MOODS:
            data.setdefault(mood, [])
        return data
    except Exception:
        return {m: [] for m in MOODS}


def save_history(history: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def import_optional(module_name: str):
    if module_name in _MISSING_OPTIONAL_MODULES:
        return None
    try:
        return __import__(module_name)
    except Exception:
        _MISSING_OPTIONAL_MODULES.add(module_name)
        return None


def search_youtube_music(query: str, limit: int = 12) -> List[Dict[str, str]]:
    ytmusicapi = import_optional("ytmusicapi")
    if ytmusicapi is None:
        return []

    try:
        ytmusic = ytmusicapi.YTMusic()
        results = ytmusic.search(query, filter="songs", limit=limit)
    except Exception:
        return []

    tracks = []
    for item in results:
        video_id = item.get("videoId")
        title = item.get("title")
        artists = item.get("artists") or []
        artist_name = ", ".join(a.get("name", "") for a in artists if a.get("name"))
        if not (video_id and title and artist_name):
            continue
        tracks.append(
            {
                "id": f"yt:{video_id}",
                "song": title,
                "artist": artist_name,
                "url": f"https://music.youtube.com/watch?v={video_id}",
                "source": "youtube",
            }
        )
    return tracks


def search_spotify(query: str, limit: int = 10) -> List[Dict[str, str]]:
    client_id = os.environ.get("SPOTIPY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")
    if not (client_id and client_secret):
        return []

    spotipy = import_optional("spotipy")
    if spotipy is None:
        return []

    try:
        creds = spotipy.oauth2.SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(auth_manager=creds)
        data = sp.search(q=query, type="track", limit=limit, market="IN")
    except Exception:
        return []

    items = data.get("tracks", {}).get("items", [])
    tracks = []
    for track in items:
        track_id = track.get("id")
        title = track.get("name")
        artists = track.get("artists", [])
        artist_name = ", ".join(a.get("name", "") for a in artists if a.get("name"))
        url = (track.get("external_urls") or {}).get("spotify")
        if not (track_id and title and artist_name and url):
            continue
        tracks.append(
            {
                "id": f"sp:{track_id}",
                "song": title,
                "artist": artist_name,
                "url": url,
                "source": "spotify",
            }
        )
    return tracks


def collect_candidates(mood: str, user_text: str, platform: str) -> List[Dict[str, str]]:
    queries = list(MOOD_QUERIES[mood])
    hint = normalize(user_text)
    if hint:
        queries.append(f"{mood} {hint[:40]} hindi song")

    candidates: List[Dict[str, str]] = []
    for query in queries:
        if platform == "spotify":
            candidates.extend(search_spotify(query, limit=8))
        elif platform == "youtube":
            candidates.extend(search_youtube_music(query, limit=12))
        else:
            candidates.extend(search_spotify(query, limit=6))
            candidates.extend(search_youtube_music(query, limit=10))

    seen = set()
    deduped = []
    for track in candidates:
        if track["id"] in seen:
            continue
        seen.add(track["id"])
        deduped.append(track)
    return deduped


def pick_track(mood: str, user_text: str, history: dict, platform: str) -> Dict[str, str]:
    candidates = collect_candidates(mood, user_text, platform)
    if not candidates:
        q = random.choice(MOOD_QUERIES[mood])
        if platform == "spotify":
            url = "https://open.spotify.com/search/" + urllib.parse.quote(q)
            return {
                "id": f"fallback:{mood}:spotify",
                "song": "Mood Mix (Live Search)",
                "artist": "Spotify",
                "url": url,
                "source": "spotify",
            }

        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q)
        return {
            "id": f"fallback:{mood}",
            "song": "Mood Mix (Live Search)",
            "artist": "YouTube",
            "url": url,
            "source": "youtube",
        }

    recent = deque(history.get(mood, []), maxlen=MAX_RECENT)
    fresh = [t for t in candidates if t["id"] not in recent]
    chosen = random.choice(fresh if fresh else candidates)
    recent.append(chosen["id"])
    history[mood] = list(recent)
    return chosen


def auto_play(url: str) -> bool:
    try:
        return webbrowser.open(url, new=2)
    except Exception:
        return False


def select_mood_interactive() -> str:
    print("Choose mood:")
    for idx, mood in enumerate(MOODS, start=1):
        print(f"{idx}. {mood}")

    while True:
        choice = input("Enter mood number (1-5): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(MOODS):
            return MOODS[int(choice) - 1]
        print("Invalid choice. Try again.")


def select_platform_interactive() -> str:
    print("Choose platform:")
    print("1. youtube")
    print("2. spotify")
    print("3. auto")

    while True:
        choice = input("Enter platform number (1-3): ").strip()
        if choice == "1":
            return "youtube"
        if choice == "2":
            return "spotify"
        if choice == "3":
            return "auto"
        print("Invalid choice. Try again.")


def run(
    his_name: str,
    user_text: str = "",
    forced_mood: Optional[str] = None,
    platform: str = "auto",
    reset_history: bool = False,
    no_autoplay: bool = False,
) -> dict:
    if reset_history and HISTORY_PATH.exists():
        HISTORY_PATH.unlink(missing_ok=True)

    mood = forced_mood if forced_mood in MOODS else detect_mood_from_text(user_text)
    history = load_history()
    pick = pick_track(mood, user_text, history, platform)
    save_history(history)

    llm_message, llm_error = llm_generate_message(his_name, mood, user_text)
    message = llm_message or fallback_message(his_name, mood)

    played = False
    if not no_autoplay:
        played = auto_play(pick["url"])

    warning = None
    if platform == "spotify" and pick["source"] != "spotify":
        warning = "Spotify results unavailable, switched source."
    if platform == "spotify" and pick["source"] == "spotify" and pick["song"] == "Mood Mix (Live Search)":
        warning = "No direct Spotify tracks found. Opened Spotify search results."

    return {
        "mood": mood,
        "song": pick["song"],
        "artist": pick["artist"],
        "message": message,
        "autoplay": True,
        "url": pick["url"],
        "source": pick["source"],
        "platform_requested": platform,
        "playback_started": played,
        "warning": warning,
        "llm_used": bool(llm_message),
        "llm_fallback_reason": llm_error,
    }


def main() -> None:
    load_env_file()

    parser = argparse.ArgumentParser(description="Smart Music Box")
    parser.add_argument("--name", required=True, help="His name")
    parser.add_argument("--text", default="", help="Optional user text context")
    parser.add_argument("--mood", choices=MOODS, help="Select mood directly")
    parser.add_argument("--platform", choices=["youtube", "spotify", "auto"], default="auto")
    parser.add_argument("--interactive", action="store_true", help="Interactive mood/platform selection")
    parser.add_argument("--reset-history", action="store_true", help="Reset recent song history")
    parser.add_argument("--no-autoplay", action="store_true", help="Do not open browser for playback")
    args = parser.parse_args()

    chosen_mood = args.mood
    chosen_platform = args.platform

    if args.interactive or not args.mood:
        chosen_mood = select_mood_interactive()
        chosen_platform = select_platform_interactive()

    result = run(
        his_name=args.name,
        user_text=args.text,
        forced_mood=chosen_mood,
        platform=chosen_platform,
        reset_history=args.reset_history,
        no_autoplay=args.no_autoplay,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
