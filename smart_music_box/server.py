import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

try:
    from smart_music_box.main import MOODS, load_env_file, run
except ModuleNotFoundError:
    from main import MOODS, load_env_file, run

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_NAME = os.environ.get("DEFAULT_NAME", "Bacchu")


class SmartMusicHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def _json_response(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/generate":
            self._json_response(404, {"error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(raw_body or "{}")

            mood = str(data.get("mood", "")).strip().lower()
            platform = str(data.get("platform", "auto")).strip().lower()
            name = str(data.get("name", DEFAULT_NAME)).strip() or DEFAULT_NAME
            user_text = str(data.get("text", "")).strip()

            if mood not in MOODS:
                self._json_response(400, {"error": "Invalid mood"})
                return
            if platform not in {"youtube", "spotify", "auto"}:
                self._json_response(400, {"error": "Invalid platform"})
                return

            result = run(
                his_name=name,
                user_text=user_text,
                forced_mood=mood,
                platform=platform,
                no_autoplay=True,
            )
            self._json_response(200, result)
        except json.JSONDecodeError:
            self._json_response(400, {"error": "Invalid JSON body"})
        except Exception as exc:
            self._json_response(500, {"error": f"Server error: {exc}"})


def main() -> None:
    load_env_file()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))

    server = ThreadingHTTPServer((host, port), SmartMusicHandler)
    print(f"Smart Music Box running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
