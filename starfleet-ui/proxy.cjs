const http = require('http');
const fs = require('fs');
const path = require('path');

const API_PORT = 8787;
const SERVE_PORT = 5173;
const DIST = path.join(__dirname, 'dist');
const API_ROUTES = ['/operator', '/chat', '/admin', '/mcp'];

const MIME = {
  '.html':'text/html','.js':'application/javascript','.css':'text/css',
  '.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml',
  '.ico':'image/x-icon','.json':'application/json','.woff2':'font/woff2','.woff':'font/woff'
};

function proxyToApi(req, res) {
  const opts = {
    hostname: '127.0.0.1', port: API_PORT,
    path: req.url, method: req.method,
    headers: req.headers
  };
  const proxy = http.request(opts, r => {
    res.writeHead(r.statusCode, r.headers);
    r.pipe(res);
  });
  proxy.on('error', e => { res.writeHead(502); res.end('API error: ' + e.message); });
  req.pipe(proxy);
}

function serveStatic(req, res) {
  let filePath = path.join(DIST, req.url.split('?')[0]);
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(DIST, 'index.html');
  }
  const ext = path.extname(filePath);
  const mime = MIME[ext] || 'application/octet-stream';
  fs.readFile(filePath, (err, data) => {
    if (err) { res.writeHead(404); res.end('Not found'); return; }
    res.writeHead(200, {'Content-Type': mime});
    res.end(data);
  });
}

http.createServer((req, res) => {
  const isApi = API_ROUTES.some(r => req.url.startsWith(r));
  if (isApi) proxyToApi(req, res);
  else serveStatic(req, res);
}).listen(SERVE_PORT, () => console.log('Proxy running on ' + SERVE_PORT));
