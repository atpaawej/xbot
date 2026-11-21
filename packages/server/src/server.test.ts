import { test, describe, before, after } from 'node:test';
import * as assert from 'node:assert';
import { WebSocket } from 'ws';
import { createAppServer, type AppServer } from './server.js';
import type { ServerMessage, ClientMessage } from '@xbot/shared';

describe('Server Application Gateway & End-to-End Chat Tracer Bullet', () => {
  let app: AppServer;
  let port: number;

  before(async () => {
    // Start server with in-memory database and 0ms chunk delay for instant deterministic tests
    app = createAppServer({
      dbPath: ':memory:',
      port: 0,
      chunkDelayMs: 0,
    });
    port = await app.start();
  });

  after(async () => {
    await app.close();
  });

  function createClient(): Promise<{ ws: WebSocket; send: (msg: ClientMessage) => void }> {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(`ws://localhost:${port}/ws`);
      ws.on('open', () => {
        resolve({
          ws,
          send: (msg: ClientMessage) => ws.send(JSON.stringify(msg)),
        });
      });
      ws.on('error', reject);
    });
  }

  function waitForMessage(ws: WebSocket, predicate: (msg: ServerMessage) => boolean, timeoutMs = 2000): Promise<ServerMessage> {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(`Timed out after ${timeoutMs}ms waiting for matching message`));
      }, timeoutMs);

      const handler = (data: any) => {
        const raw = typeof data === 'string' ? data : data.toString('utf-8');
        try {
          const parsed = JSON.parse(raw) as ServerMessage;
          if (predicate(parsed)) {
            clearTimeout(timer);
            ws.off('message', handler);
            resolve(parsed);
          }
        } catch {
          // ignore parsing error while waiting
        }
      };

      ws.on('message', handler);
    });
  }

  test('health endpoint returns 200 OK', async () => {
    const res = await fetch(`http://localhost:${port}/health`);
    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.strictEqual(body.status, 'ok');
  });

  test('retrieves default seeded bots via WebSocket', async () => {
    const { ws, send } = await createClient();
    try {
      const responsePromise = waitForMessage(ws, (m) => m.type === 'bots.list.response');
      send({ type: 'bots.list' });

      const response = (await responsePromise) as Extract<ServerMessage, { type: 'bots.list.response' }>;
      assert.strictEqual(response.type, 'bots.list.response');
      assert.ok(response.bots.length >= 7, 'Expected at least 7 seeded bots');

      const firstmate = response.bots.find((b) => b.id === 'firstmate-oss');
      assert.ok(firstmate, 'firstmate-oss bot should be present');
      assert.strictEqual(firstmate?.name, 'firstmate-oss');
      assert.strictEqual(firstmate?.icon, 'flame');
    } finally {
      ws.close();
    }
  });

  test('restores conversation history on demand (persistence)', async () => {
    const { ws, send } = await createClient();
    try {
      const responsePromise = waitForMessage(ws, (m) => m.type === 'history.get.response');
      send({ type: 'history.get', sessionId: 'session-firstmate-oss-initial' });

      const response = (await responsePromise) as Extract<ServerMessage, { type: 'history.get.response' }>;
      assert.strictEqual(response.type, 'history.get.response');
      assert.strictEqual(response.sessionId, 'session-firstmate-oss-initial');
      assert.ok(response.messages.length >= 2, 'Initial conversation must have messages');

      assert.strictEqual(response.messages[0].role, 'user');
      assert.ok(response.messages[0].content.includes('fleet triage'));

      assert.strictEqual(response.messages[1].role, 'bot');
      assert.ok(response.messages[1].content.includes('Roughly 2,100 items') || response.messages[1].content.includes('2,100 items'));
    } finally {
      ws.close();
    }
  });

  test('handles chat.send by streaming chunks and persisting bot response', async () => {
    const { ws, send } = await createClient();
    try {
      const sessionId = 'session-firstmate-oss-initial';
      const testPrompt = 'Status check on current fleet workers';

      // Collect stream chunks
      const streamDeltas: string[] = [];
      const donePromise = waitForMessage(ws, (m) => m.type === 'chat.done');

      const streamHandler = (data: any) => {
        try {
          const parsed = JSON.parse(data.toString('utf-8')) as ServerMessage;
          if (parsed.type === 'chat.stream') {
            streamDeltas.push(parsed.delta);
          }
        } catch {}
      };
      ws.on('message', streamHandler);

      // Send chat prompt
      send({
        type: 'chat.send',
        sessionId,
        botId: 'firstmate-oss',
        content: testPrompt,
      });

      const doneMsg = (await donePromise) as Extract<ServerMessage, { type: 'chat.done' }>;
      ws.off('message', streamHandler);

      assert.strictEqual(doneMsg.type, 'chat.done');
      assert.strictEqual(doneMsg.sessionId, sessionId);
      assert.strictEqual(doneMsg.message.role, 'bot');
      assert.ok(doneMsg.message.content.length > 0, 'Bot response content should not be empty');
      assert.ok(streamDeltas.length > 0, 'Expected to receive multiple streaming deltas');

      // Verify conversation was persisted to SQLite database
      const history = app.db.listMessages(sessionId);
      const lastUserMsg = history[history.length - 2];
      const lastBotMsg = history[history.length - 1];

      assert.strictEqual(lastUserMsg.role, 'user');
      assert.strictEqual(lastUserMsg.content, testPrompt);
      assert.strictEqual(lastBotMsg.role, 'bot');
      assert.strictEqual(lastBotMsg.content, doneMsg.message.content);
    } finally {
      ws.close();
    }
  });

  test('rejects empty message with error response', async () => {
    const { ws, send } = await createClient();
    try {
      const errorPromise = waitForMessage(ws, (m) => m.type === 'error');
      send({
        type: 'chat.send',
        sessionId: 'session-firstmate-oss-initial',
        botId: 'firstmate-oss',
        content: '   ',
      });

      const errorMsg = (await errorPromise) as Extract<ServerMessage, { type: 'error' }>;
      assert.strictEqual(errorMsg.type, 'error');
      assert.ok(errorMsg.message.includes('cannot be empty'));
    } finally {
      ws.close();
    }
  });

  test('gracefully rejects invalid bot id without crashing daemon', async () => {
    const { ws, send } = await createClient();
    try {
      const errorPromise = waitForMessage(ws, (m) => m.type === 'error');
      send({
        type: 'chat.send',
        sessionId: 'session-firstmate-oss-initial',
        botId: 'non-existent-bot',
        content: 'Hello bot',
      });

      const errorMsg = (await errorPromise) as Extract<ServerMessage, { type: 'error' }>;
      assert.strictEqual(errorMsg.type, 'error');
      assert.ok(errorMsg.message.includes('not found'));
    } finally {
      ws.close();
    }
  });
});
