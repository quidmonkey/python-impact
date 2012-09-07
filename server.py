import cgi
import glob
import http.server
import json
import mimetypes
import os
import socketserver
import sys
from urllib.parse import parse_qs

# Various config settings for the python server
SETTINGS = {
    "port":        8080,
    "logging":     False,

    "api-save":    "/lib/weltmeister/api/save.php",
    "api-browse":  "/lib/weltmeister/api/browse.php",
    "api-glob":    "/lib/weltmeister/api/glob.php",

    "image-types": [".png", ".jpg", ".gif", ".jpeg"]
}

# Blank favicon - prevents 404s from occuring if no favicon is supplied
BLANK_FAVICON = "GIF89a\x01\x00\x01\x00\xf0\x00\x00\xff\xff\xff\x00\x00\x00!\xff\x0bXMP DataXMP\x02?x\x00!\xf9\x04\x05\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00@\x02\x02D\x01\x00;"

class HTTPHandler(http.server.BaseHTTPRequestHandler):

    def browse(self):
        # Get the directory from POST parameters
        dir = self.query_params['dir'][0] if 'dir' in self.query_params else '.'
        dir = dir.replace('..', '')

        # Locate dir
        if dir != '.' :
            dir = self.locate_dir(dir)

        # Add slash
        if dir[-1] != os.sep:
            dir += os.sep

        # If editor's been reloaded, skip file re-POST
        if not os.path.isdir(dir):
            return

        # Unpack dir
        dirs = [d for d in os.listdir(dir) if '.' not in d]
        files = glob.glob(dir + '*.*')

        # Filter on file types
        if 'type' in self.query_params:
            types = self.query_params['type']
            if 'images' in types:
                files = [f for f in files if os.path.splitext(f)[1] in SETTINGS['image-types']]
            elif 'scripts' in types:
                files = [f for f in files if os.path.splitext(f)[1] == '.js']

        # Normalize file paths
        dirs = [os.path.normpath(d) for d in dirs]
        files = [os.path.normpath(f) for f in files]

        # Create response
        response = {
            'files': files,
            'dirs': dirs,
            'parent': False if dir == './' else os.path.dirname(os.path.dirname(dir))
        }
        return self.send_json(response)

    def do_GET(self):
        self.init_request()
        self.route_request('GET')

    def do_POST(self):
        self.init_request()

        # From http://stackoverflow.com/questions/4233218/python-basehttprequesthandler-post-variables
        # Grab content-type and content-length from self.headers dictionary
        ctype, pdict = cgi.parse_header(self.headers['content-type'])
        if ctype == 'multipart/form-data':
            self.post_params = cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            self.post_params = parse_qs(self.rfile.read(length), keep_blank_values = True)

        self.route_request('POST')

    def glob(self):
        globs = self.query_params['glob[]']
        files = []

        for g in globs:
            g = g.replace('..', '')
            more = glob.glob(g)
            files.extend(more)

        # Format to Windows file structure
        if os.name == 'nt':
            files = [f.replace('\\', '/') for f in files]

        return self.send_json(files)

    def init_request(self):
        parts = self.path.split('?', 1)
        self.post_params = {}
        if len(parts) == 1:
            self.file_path = parts[0]
            self.query_params = {}
        else:
            self.file_path = parts[0]
            self.query_params = parse_qs(parts[1])

    def locate_dir(self, dir):
        '''Locate passed-in directory relative to current script.
            Returns passed-in dir if no path is found.'''
        for root, dirs, files in os.walk('.'):
            for d in dirs:
                if( d == dir ):
                    return os.path.join( root, d )
        return 

    def log_request(self, *args, **kwargs):
        '''If logging is disabled'''
        if SETTINGS['logging']:
            self.log_request(*args, **kwargs)

    def route_request(self, method = 'GET'):
        if self.file_path == SETTINGS['api-save']:
            self.save()
        elif self.file_path == SETTINGS['api-browse']:
            self.browse()
        elif self.file_path == SETTINGS['api-glob']:
            self.glob()
        elif method == 'GET':
            self.serve_file()
        else:
            self.illegal()

    def save(self):
        resp = {'error': 0}
        # Look for byte keys
        if b'path' in self.post_params and b'data' in self.post_params:
            # Convert from bytes to string
            path = self.post_params[b'path'][0].decode('utf-8')
            path = os.curdir + os.sep + path.replace('..', '')
            data = self.post_params[b'data'][0].decode('utf-8')

            if path.endswith('.js'):
                try:
                    open(path, 'w').write(data)
                except:
                    resp['error'] = 2
                    resp['msg'] = "Couldn't write to file %s" % path

            else:
                resp['error'] = 3
                resp['msg'] = 'File must have a .js suffix'

        else:
            resp['error'] = 1
            resp['msg'] = 'No Data or Path specified'

        return self.send_json(resp)

    def send_json(self, obj, code = 200, headers = None):
        '''Send response as JSON'''
        if not headers:
            headers = {}
        headers['Content-Type'] = 'application/json'
        self.send_response(json.dumps(obj).encode('utf-8'), code, headers)

    def send_response(self, data, code = 200, headers = None):
        '''Wraps sending a response down'''
        if not headers:
            headers = {}
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'text/html'
        http.server.BaseHTTPRequestHandler.send_response(self, code)
        self.send_header('Content-Length', len(data))
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def serve_file(self):
        path = self.file_path
        if path == '/':
            path = 'index.html'
        elif path == '/editor':
            path = 'weltmeister.html'

        # Remove the leading forward slash
        if path[0] == '/':
            path = path[1:]

        # Security, remove the ..
        path = path.replace('..', '')

        # Determine the relative path
        path = os.curdir + os.sep + path

        try:
            data = open(path, 'rb').read()
            type, _ = mimetypes.guess_type(path)
            self.send_response(data, 200, headers = {'Content-Type': type})
        except:
            if os.sep + 'favicon.ico' in path:
                self.send_response(BLANK_FAVICON.encode('utf-8'), 200, headers = {"Content-Type": "image/gif"})
            else:
                self.send_response('', 404)

    def illegal(self):
        self.send_response('Method Not Allowed', 405)

def main():
    addr = ('', SETTINGS['port'])
    server = http.server.HTTPServer(addr, HTTPHandler)
    print('Running ImpactJS Server\nGame:\thttp://localhost:%d\nEditor:\thttp://localhost:%d/editor' % (addr[1], addr[1]))
    server.serve_forever()

if __name__ == '__main__':
    main()