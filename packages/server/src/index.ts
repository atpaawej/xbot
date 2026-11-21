import { createAppServer } from './server.js';
import * as path from 'node:path';

const PORT = parseInt(process.env.PORT || '3001', 10);
const DB_PATH = process.env.DB_PATH || path.resolve(process.cwd(), 'data/xbot.db');

const app = createAppServer({
  port: PORT,
  dbPath: DB_PATH,
  chunkDelayMs: 25,
});

app.start().then((port) => {
  console.log(`[xbot-server] daemon started on http://localhost:${port}`);
  console.log(`[xbot-server] WebSocket endpoint: ws://localhost:${port}/ws`);
  console.log(`[xbot-server] SQLite database: ${DB_PATH}`);
});

process.on('SIGINT', async () => {
  console.log('\n[xbot-server] shutting down gracefully...');
  await app.close();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  await app.close();
  process.exit(0);
});
