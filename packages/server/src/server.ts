import * as http from 'node:http';
import { WebSocketServer, WebSocket } from 'ws';
import type { ClientMessage, ServerMessage, Message } from '@xbot/shared';
import { createDatabase, type DatabaseService } from './db.js';
import { simulateBotStream } from './simulator.js';

export interface AppServerOptions {
  dbPath?: string;
  port?: number;
  chunkDelayMs?: number;
}

export interface AppServer {
  httpServer: http.Server;
  wss: WebSocketServer;
  db: DatabaseService;
  port: number;
  start(): Promise<number>;
  close(): Promise<void>;
}

export function createAppServer(options: AppServerOptions = {}): AppServer {
  const db = createDatabase(options.dbPath ?? 'data/xbot.db');
  const chunkDelayMs = options.chunkDelayMs ?? 20;

  const httpServer = http.createServer((req, res) => {
    // CORS headers for local frontend dev server
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
      res.writeHead(204);
      res.end();
      return;
    }

    const url = new URL(req.url ?? '/', `http://${req.headers.host || 'localhost'}`);

    if (url.pathname === '/health') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ok', time: new Date().toISOString() }));
      return;
    }

    if (url.pathname === '/api/bots' && req.method === 'GET') {
      const bots = db.listBots();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ bots }));
      return;
    }

    if (url.pathname.startsWith('/api/sessions/') && url.pathname.endsWith('/messages') && req.method === 'GET') {
      const parts = url.pathname.split('/');
      const sessionId = parts[3];
      if (!sessionId) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Session ID required' }));
        return;
      }
      const messages = db.listMessages(sessionId);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ messages }));
      return;
    }

    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not Found' }));
  });

  const wss = new WebSocketServer({ server: httpServer, path: '/ws' });

  wss.on('connection', (ws: WebSocket) => {
    const send = (msg: ServerMessage) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(msg));
      }
    };

    ws.on('message', async (data: Buffer | string) => {
      try {
        const raw = typeof data === 'string' ? data : data.toString('utf-8');
        const clientMsg: ClientMessage = JSON.parse(raw);

        switch (clientMsg.type) {
          case 'bots.list': {
            const bots = db.listBots();
            send({ type: 'bots.list.response', bots });
            break;
          }

          case 'sessions.list': {
            const sessions = db.listSessions(clientMsg.botId);
            send({ type: 'sessions.list.response', sessions });
            break;
          }

          case 'history.get': {
            const messages = db.listMessages(clientMsg.sessionId);
            send({ type: 'history.get.response', sessionId: clientMsg.sessionId, messages });
            break;
          }

          case 'chat.send': {
            const { sessionId, botId, content } = clientMsg;

            if (!content || !content.trim()) {
              send({ type: 'error', message: 'Message content cannot be empty.' });
              return;
            }

            const bot = db.getBot(botId);
            if (!bot) {
              send({ type: 'error', message: `Bot '${botId}' not found.` });
              return;
            }

            // 1. Create and persist user message
            const userMsgId = `msg-user-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
            const userMsg: Message = {
              id: userMsgId,
              sessionId,
              role: 'user',
              content: content.trim(),
              createdAt: new Date().toISOString(),
            };
            db.saveMessage(userMsg);

            // Acknowledge user message immediately
            send({ type: 'chat.ack', sessionId, message: userMsg });

            // 2. Stream bot response
            const botMsgId = `msg-bot-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
            let finalContent = '';

            try {
              for await (const chunk of simulateBotStream(userMsg.content, bot, { chunkDelayMs })) {
                finalContent = chunk.fullContent;
                send({
                  type: 'chat.stream',
                  sessionId,
                  messageId: botMsgId,
                  delta: chunk.delta,
                  fullContent: chunk.fullContent,
                });
              }

              // 3. Persist complete bot message
              const botMsg: Message = {
                id: botMsgId,
                sessionId,
                role: 'bot',
                content: finalContent,
                createdAt: new Date().toISOString(),
              };
              db.saveMessage(botMsg);

              // 4. Send completion event
              send({ type: 'chat.done', sessionId, message: botMsg });
            } catch (err: any) {
              send({ type: 'error', message: `Stream failure: ${err?.message || 'unknown error'}` });
            }
            break;
          }

          default:
            send({ type: 'error', message: `Unknown message type` });
            break;
        }
      } catch (err: any) {
        send({ type: 'error', message: `Malformed JSON: ${err?.message || 'parse error'}` });
      }
    });
  });

  return {
    httpServer,
    wss,
    db,
    port: options.port ?? 3001,
    start(): Promise<number> {
      return new Promise((resolve) => {
        httpServer.listen(this.port, () => {
          const address = httpServer.address();
          const actualPort = typeof address === 'object' && address ? address.port : this.port;
          this.port = actualPort;
          resolve(actualPort);
        });
      });
    },
    close(): Promise<void> {
      return new Promise((resolve) => {
        wss.close(() => {
          httpServer.close(() => {
            db.close();
            resolve();
          });
        });
      });
    },
  };
}
