from http.server import BaseHTTPRequestHandler

# This is the minimal handler that Vercel looks for
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Flask App is online! Please access the main app at the root URL.')
        return 