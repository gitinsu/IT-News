const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3000;

const server = http.createServer((req, res) => {
  // CORS 헤더 항상 추가
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // preflight 요청 처리
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // HTML 파일 서빙
  if (req.method === 'GET' && (req.url === '/' || req.url === '/index.html')) {
    const filePath = path.join(__dirname, 'it-news-live.html');
    fs.readFile(filePath, 'utf-8', (err, data) => {
      if (err) {
        res.writeHead(404);
        res.end('it-news-live.html 파일을 찾을 수 없어요. 같은 폴더에 있는지 확인해주세요.');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(data, 'utf-8');
    });
    return;
  }

  // Gemini API 프록시 (스트리밍)
  if (req.method === 'POST' && req.url === '/gemini') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        const { apiKey, payload } = JSON.parse(body);

        const options = {
          hostname: 'generativelanguage.googleapis.com',
          path: `/v1beta/models/gemini-2.0-flash:streamGenerateContent?key=${apiKey}&alt=sse`,
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        };

        const proxyReq = https.request(options, proxyRes => {
          res.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
          });
          proxyRes.pipe(res);
        });

        proxyReq.on('error', err => {
          res.writeHead(500);
          res.end(JSON.stringify({ error: err.message }));
        });

        proxyReq.write(payload);
        proxyReq.end();

      } catch (e) {
        res.writeHead(400);
        res.end(JSON.stringify({ error: '잘못된 요청입니다.' }));
      }
    });
    return;
  }

  res.writeHead(404);
  res.end('Not found');
});

server.listen(PORT, () => {
  console.log('');
  console.log('✅ IT PULSE 서버 실행 중!');
  console.log('');
  console.log('👉 브라우저에서 아래 주소로 접속하세요:');
  console.log(`   http://localhost:${PORT}`);
  console.log('');
  console.log('서버를 끄려면 Ctrl+C 를 누르세요.');
  console.log('');
});
