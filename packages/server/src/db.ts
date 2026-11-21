import { DatabaseSync } from 'node:sqlite';
import * as fs from 'node:fs';
import * as path from 'node:path';
import type { Bot, Session, Message } from '@xbot/shared';

export interface DatabaseService {
  db: DatabaseSync;
  listBots(): Bot[];
  getBot(id: string): Bot | null;
  createBot(bot: Bot): void;
  listSessions(botId?: string): Session[];
  getSession(id: string): Session | null;
  getOrCreateSession(botId: string): Session;
  listMessages(sessionId: string): Message[];
  saveMessage(message: Message): void;
  close(): void;
}

export function createDatabase(dbPath: string = ':memory:'): DatabaseService {
  if (dbPath !== ':memory:') {
    const dir = path.dirname(dbPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }

  const db = new DatabaseSync(dbPath);

  // Enable WAL mode and foreign keys for file-backed DB
  if (dbPath !== ':memory:') {
    db.exec('PRAGMA journal_mode = WAL;');
  }
  db.exec('PRAGMA foreign_keys = ON;');

  // Initialize tables
  db.exec(`
    CREATE TABLE IF NOT EXISTS bots (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT,
      icon TEXT NOT NULL,
      color TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'idle',
      system_prompt TEXT,
      harness_command TEXT,
      workspace_path TEXT,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sessions (
      id TEXT PRIMARY KEY,
      bot_id TEXT NOT NULL,
      title TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY (bot_id) REFERENCES bots(id)
    );

    CREATE TABLE IF NOT EXISTS messages (
      id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      role TEXT NOT NULL,
      content TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (session_id) REFERENCES sessions(id)
    );

    CREATE INDEX IF NOT EXISTS idx_sessions_bot_id ON sessions(bot_id);
    CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
  `);

  // Seed default bots if empty
  const countRow = db.prepare('SELECT COUNT(*) as count FROM bots').get() as { count: number | bigint };
  const botCount = Number(countRow.count);

  if (botCount === 0) {
    seedDefaultData(db);
  }

  return {
    db,
    listBots(): Bot[] {
      const rows = db.prepare('SELECT * FROM bots ORDER BY created_at ASC').all() as any[];
      return rows.map((r) => ({
        id: r.id,
        name: r.name,
        title: r.title,
        description: r.description ?? '',
        icon: r.icon,
        color: r.color,
        status: r.status,
        systemPrompt: r.system_prompt ?? '',
        harnessCommand: r.harness_command ?? '',
        workspacePath: r.workspace_path ?? '',
        createdAt: r.created_at,
      }));
    },

    getBot(id: string): Bot | null {
      const r = db.prepare('SELECT * FROM bots WHERE id = ?').get(id) as any;
      if (!r) return null;
      return {
        id: r.id,
        name: r.name,
        title: r.title,
        description: r.description ?? '',
        icon: r.icon,
        color: r.color,
        status: r.status,
        systemPrompt: r.system_prompt ?? '',
        harnessCommand: r.harness_command ?? '',
        workspacePath: r.workspace_path ?? '',
        createdAt: r.created_at,
      };
    },

    createBot(bot: Bot): void {
      db.prepare(`
        INSERT INTO bots (id, name, title, description, icon, color, status, system_prompt, harness_command, workspace_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).run(
        bot.id,
        bot.name,
        bot.title,
        bot.description,
        bot.icon,
        bot.color,
        bot.status,
        bot.systemPrompt,
        bot.harnessCommand,
        bot.workspacePath,
        bot.createdAt
      );
    },

    listSessions(botId?: string): Session[] {
      const stmt = botId
        ? db.prepare('SELECT * FROM sessions WHERE bot_id = ? ORDER BY updated_at DESC')
        : db.prepare('SELECT * FROM sessions ORDER BY updated_at DESC');
      const rows = (botId ? stmt.all(botId) : stmt.all()) as any[];
      return rows.map((r) => ({
        id: r.id,
        botId: r.bot_id,
        title: r.title,
        createdAt: r.created_at,
        updatedAt: r.updated_at,
      }));
    },

    getSession(id: string): Session | null {
      const r = db.prepare('SELECT * FROM sessions WHERE id = ?').get(id) as any;
      if (!r) return null;
      return {
        id: r.id,
        botId: r.bot_id,
        title: r.title,
        createdAt: r.created_at,
        updatedAt: r.updated_at,
      };
    },

    getOrCreateSession(botId: string): Session {
      const existing = db.prepare('SELECT * FROM sessions WHERE bot_id = ? ORDER BY updated_at DESC LIMIT 1').get(botId) as any;
      if (existing) {
        return {
          id: existing.id,
          botId: existing.bot_id,
          title: existing.title,
          createdAt: existing.created_at,
          updatedAt: existing.updated_at,
        };
      }

      const now = new Date().toISOString();
      const newSession: Session = {
        id: `session-${botId}-${Date.now()}`,
        botId,
        title: `Conversation with ${botId}`,
        createdAt: now,
        updatedAt: now,
      };

      db.prepare(`
        INSERT INTO sessions (id, bot_id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
      `).run(newSession.id, newSession.botId, newSession.title, newSession.createdAt, newSession.updatedAt);

      return newSession;
    },

    listMessages(sessionId: string): Message[] {
      const rows = db.prepare('SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC, rowid ASC').all(sessionId) as any[];
      return rows.map((r) => ({
        id: r.id,
        sessionId: r.session_id,
        role: r.role,
        content: r.content,
        createdAt: r.created_at,
      }));
    },

    saveMessage(message: Message): void {
      db.prepare(`
        INSERT INTO messages (id, session_id, role, content, created_at)
        VALUES (?, ?, ?, ?, ?)
      `).run(message.id, message.sessionId, message.role, message.content, message.createdAt);

      // update session updatedAt
      db.prepare('UPDATE sessions SET updated_at = ? WHERE id = ?').run(message.createdAt, message.sessionId);
    },

    close(): void {
      db.close();
    },
  };
}

function seedDefaultData(db: DatabaseSync): void {
  const now = new Date().toISOString();

  const bots = [
    {
      id: 'firstmate-oss',
      name: 'firstmate-oss',
      title: 'Firstmate • OSS Lead',
      description: 'The only agent I talk to. Leads open-source fleet coordination and telemetry.',
      icon: 'flame',
      color: '#f43f5e',
      status: 'idle',
      systemPrompt: 'You are Firstmate, the autonomous fleet coordinator for xbot OSS repos.',
      harnessCommand: 'claude-code',
      workspacePath: 'workspaces/firstmate-oss',
      createdAt: '2026-11-20T10:00:00.000Z',
    },
    {
      id: 'treehouse',
      name: 'treehouse',
      title: 'Treehouse • CI Bot',
      description: 'Cross-platform Windows, Linux, and macOS build & test orchestrator.',
      icon: 'wedge',
      color: '#3b82f6',
      status: 'idle',
      systemPrompt: 'You are Treehouse, automated CI tester.',
      harnessCommand: 'goose',
      workspacePath: 'workspaces/treehouse',
      createdAt: '2026-11-20T10:05:00.000Z',
    },
    {
      id: 'runner-up',
      name: 'runner-up',
      title: 'Runner Up • Release Bot',
      description: 'Automates semantic releases, changelogs, and squash-merge pipelines.',
      icon: 'pill',
      color: '#f59e0b',
      status: 'idle',
      systemPrompt: 'You are Runner Up, release automation teammate.',
      harnessCommand: 'claude-code',
      workspacePath: 'workspaces/runner-up',
      createdAt: '2026-11-20T10:10:00.000Z',
    },
    {
      id: 'no-mistakes',
      name: 'no-mistakes',
      title: 'No Mistakes • QA Linter',
      description: 'Deep static analysis, type checking, and boundary proof verifications.',
      icon: 'droplet',
      color: '#06b6d4',
      status: 'idle',
      systemPrompt: 'You are No Mistakes, linting and verification specialist.',
      harnessCommand: 'openhands',
      workspacePath: 'workspaces/no-mistakes',
      createdAt: '2026-11-20T10:15:00.000Z',
    },
    {
      id: 'gnhf',
      name: 'gnhf',
      title: 'GNHF • Fleet Worker',
      description: 'Dependency graph validator and continuous PR integration agent.',
      icon: 'shield',
      color: '#ec4899',
      status: 'idle',
      systemPrompt: 'You are GNHF, continuous integration worker.',
      harnessCommand: 'claude-code',
      workspacePath: 'workspaces/gnhf',
      createdAt: '2026-11-20T10:20:00.000Z',
    },
    {
      id: 'gh-axi',
      name: 'gh-axi',
      title: 'GH Axi • PR Triage',
      description: 'Reviews incoming pull requests and syncs upstream git changes.',
      icon: 'star',
      color: '#8b5cf6',
      status: 'idle',
      systemPrompt: 'You are GH Axi, PR reviewer and merger.',
      harnessCommand: 'claude-code',
      workspacePath: 'workspaces/gh-axi',
      createdAt: '2026-11-20T10:25:00.000Z',
    },
    {
      id: 'backpass',
      name: 'backpass',
      title: 'Backpass • Security Watch',
      description: 'Continuous CVE scanning, secrets detection, and audit compliance.',
      icon: 'target',
      color: '#ef4444',
      status: 'idle',
      systemPrompt: 'You are Backpass, vulnerability scanner.',
      harnessCommand: 'goose',
      workspacePath: 'workspaces/backpass',
      createdAt: '2026-11-20T10:30:00.000Z',
    },
  ];

  const insertBot = db.prepare(`
    INSERT INTO bots (id, name, title, description, icon, color, status, system_prompt, harness_command, workspace_path, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  for (const b of bots) {
    insertBot.run(
      b.id,
      b.name,
      b.title,
      b.description,
      b.icon,
      b.color,
      b.status,
      b.systemPrompt,
      b.harnessCommand,
      b.workspacePath,
      b.createdAt
    );
  }

  // Create default session for firstmate-oss
  const firstmateSessionId = 'session-firstmate-oss-initial';
  db.prepare(`
    INSERT INTO sessions (id, bot_id, title, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?)
  `).run(
    firstmateSessionId,
    'firstmate-oss',
    'Fleet triage records',
    '2026-11-20T09:00:00.000Z',
    '2026-11-20T09:02:00.000Z'
  );

  // Seed the exact conversational exchange shown in the Grok Bot demo screenshot
  const insertMessage = db.prepare(`
    INSERT INTO messages (id, session_id, role, content, created_at)
    VALUES (?, ?, ?, ?, ?)
  `);

  insertMessage.run(
    'msg-firstmate-user-1',
    firstmateSessionId,
    'user',
    'how many issues and PRs in total did this fleet triage in the last month?',
    '2026-11-20T09:01:00.000Z'
  );

  insertMessage.run(
    'msg-firstmate-bot-1',
    firstmateSessionId,
    'bot',
    `Checking the fleet's records now, captain.

Captain, it comes to roughly 2,100 items over the last month: about 1,180 PRs and about 950 issues, all from outside contributors and spread across your repos.

Of those, 428 PRs were merged, 58 were closed without merging, and 341 issues were closed.

That's an upper estimate. I got it from GitHub by counting outside-contributor issues and PRs in your repos that your account commented on and that changed since Oct 12. The crew posts as you, so your own comments are counted too, including about 15 on sshhip, which you triage yourself. Some items whose last crew comment was before Oct 12 may be in there as well. The crew doesn't keep a per-item triage log, so I can't get an exact count.`,
    '2026-11-20T09:02:00.000Z'
  );

  // Seed sample sessions with recent snippet messages for other bots
  const sampleData = [
    {
      botId: 'treehouse',
      content: '#173 is now fully green and CLEAN too (Windows & Linux x64 runners passing).',
    },
    {
      botId: 'runner-up',
      content: 'runner-up 0.1.12 is out. I squash-merged release tags and triggered distribution.',
    },
    {
      botId: 'no-mistakes',
      content: 'no-mistakes 1.111.0 is released. All boundary type checks clean without warnings.',
    },
    {
      botId: 'gnhf',
      content: 'I released gnhf 0.1.52 by merging #249 as commit 4b1c8f.',
    },
    {
      botId: 'gh-axi',
      content: 'gh-axi 0.1.48 is out. I merged #244 as bb8c797 and cleaned up stale branch.',
    },
    {
      botId: 'backpass',
      content: 'I audited the latest dependencies. 0 critical vulnerabilities reported in workspace.',
    },
  ];

  for (const s of sampleData) {
    const sId = `session-${s.botId}-initial`;
    db.prepare(`
      INSERT INTO sessions (id, bot_id, title, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?)
    `).run(sId, s.botId, `Sync with ${s.botId}`, now, now);

    insertMessage.run(`msg-${s.botId}-init`, sId, 'bot', s.content, now);
  }
}
