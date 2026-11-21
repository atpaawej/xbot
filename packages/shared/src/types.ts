export type BotStatus = 'idle' | 'running' | 'offline';

export interface Bot {
  id: string;
  name: string;
  title: string;
  description: string;
  icon: string;
  color: string;
  status: BotStatus;
  systemPrompt: string;
  harnessCommand: string;
  workspacePath: string;
  createdAt: string;
}

export interface Session {
  id: string;
  botId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export type MessageRole = 'user' | 'bot' | 'system';

export interface Message {
  id: string;
  sessionId: string;
  role: MessageRole;
  content: string;
  createdAt: string;
}

export type ClientMessage =
  | { type: 'bots.list' }
  | { type: 'sessions.list'; botId: string }
  | { type: 'history.get'; sessionId: string }
  | { type: 'chat.send'; sessionId: string; botId: string; content: string };

export type ServerMessage =
  | { type: 'bots.list.response'; bots: Bot[] }
  | { type: 'sessions.list.response'; sessions: Session[] }
  | { type: 'history.get.response'; sessionId: string; messages: Message[] }
  | { type: 'chat.ack'; sessionId: string; message: Message }
  | { type: 'chat.stream'; sessionId: string; messageId: string; delta: string; fullContent: string }
  | { type: 'chat.done'; sessionId: string; message: Message }
  | { type: 'error'; message: string };
