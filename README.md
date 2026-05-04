# Smart Music Box

Interactive mood-first music experience:
- Shows mood options first
- You choose mood and platform (YouTube / Spotify / auto)
- Picks a dynamic matching song
- Frontend controls playback (Spotify opens tab, YouTube embeds)
- Generates a fresh LLM message for that mood

## Setup (.env)

Create `.env` in project root:

```env
HF_TOKEN=your_huggingface_token
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.3
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
DEFAULT_NAME=Bacchu
PORT=8000
```

## Optional dependencies

```bash
python -m pip install ytmusicapi
python -m pip install spotipy
```

## Run Full App (one command)

```bash
python smart_music_box/server.py
```

Then open:

```text
http://127.0.0.1:8000
```

## API

`POST /generate`

Request:

```json
{
  "mood": "happy",
  "platform": "spotify",
  "name": "Bacchu",
  "text": "optional context"
}
```

## CLI mode (optional)

```bash
python smart_music_box/main.py --name "Bacchu" --interactive
```
