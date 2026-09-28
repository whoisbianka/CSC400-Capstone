"""Local-only demo server. Run: python3 backend/server.py"""
import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

try:
    from .search import ROOT, load_programs, search
except ImportError:
    from search import ROOT, load_programs, search

PROGRAMS = load_programs()
PAGES = {'index.html', 'explore.html', 'profile.html', 'settings.html', 'program-details.html'}


class Handler(BaseHTTPRequestHandler):
    def send_content(self, status, data, content_type='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status, value):
        self.send_content(status, json.dumps(value).encode())

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path == '/api/health':
            return self.send_json(200, {'status': 'ok', 'engine': 'python', 'demo': True})
        if path == '/api/programs':
            return self.send_json(200, {'programs': PROGRAMS, 'demo': True})
        if path == '/assets/js/backend-config.js':
            return self.send_content(200, b'window.DEMO_API_ENABLED = true;\n', 'text/javascript; charset=utf-8')
        relative = path.lstrip('/') or 'index.html'
        file = (ROOT / relative).resolve()
        # Serve only public pages/assets; never expose .git or Python sources.
        allowed = (relative in PAGES or relative.startswith('assets/')) and not any(part.startswith('.') for part in relative.split('/'))
        if not allowed or not file.is_relative_to(ROOT) or not file.is_file():
            return self.send_json(404, {'error': 'Not found'})
        self.send_content(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or 'application/octet-stream')

    def do_POST(self):
        if urlsplit(self.path).path != '/api/search':
            return self.send_json(404, {'error': 'Not found'})
        if self.headers.get_content_type() != 'application/json':
            return self.send_json(415, {'error': 'Use application/json'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.send_json(400, {'error': 'Invalid content length'})
        if not 0 < size <= 65536:
            return self.send_json(413, {'error': 'Body must be between 1 and 65536 bytes'})
        try:
            body = json.loads(self.rfile.read(size))
        except (ValueError, UnicodeDecodeError):
            return self.send_json(400, {'error': 'Invalid JSON'})
        question = body.get('question') if isinstance(body, dict) else None
        if not isinstance(question, str) or not question.strip() or len(question) > 12000:
            return self.send_json(400, {'error': 'question must contain 1–12000 characters'})
        self.send_json(200, search(question.strip(), PROGRAMS))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    with ThreadingHTTPServer(('127.0.0.1', args.port), Handler) as server:
        print(f'Python demo: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
