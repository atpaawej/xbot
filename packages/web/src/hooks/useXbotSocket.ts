import { useEffect, useRef, useState, useCallback } from 'react';
import type { Bot, Message, ClientMessage, ServerMessage } from '@xbot/shared';

export function useXbotSocket() {
  const [bots, setBots] = useState<Bot[]>([]);
  const [activeBotId, setActiveBotId] = useState<string>('firstmate-oss');
  const [activeSessionId, setActiveSessionId] = useState<string>('session-firstmate-oss-initial');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | undefined>();
  const [streamingContent, setStreamingContent] = useState<string>('');
  const [recentMessages, setRecentMessages] = useState<Record<string, string>>({});
  const [isConnected, setIsConnected] = useState<boolean>(false);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  const send = useCallback((msg: ClientMessage) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const connect = useCallback(() => {
    // Connect to WebSocket server (defaults to port 3001 in dev if on 5173, or host)
    const host = window.location.port === '5173' ? 'localhost:3001' : window.location.host;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${host}/ws`;

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      // Fetch available bots
      send({ type: 'bots.list' });
      // Fetch initial conversation history for default bot session
      send({ type: 'history.get', sessionId: activeSessionId });
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as ServerMessage;

        switch (msg.type) {
          case 'bots.list.response': {
            setBots(msg.bots);
            break;
          }

          case 'history.get.response': {
            setMessages(msg.messages);
            if (msg.messages.length > 0) {
              const lastMsg = msg.messages[msg.messages.length - 1];
              setRecentMessages((prev) => ({
                ...prev,
                [activeBotId]: lastMsg.content.slice(0, 50) + '...',
              }));
            }
            break;
          }

          case 'chat.ack': {
            setMessages((prev) => {
              if (prev.some((m) => m.id === msg.message.id)) return prev;
              return [...prev, msg.message];
            });
            break;
          }

          case 'chat.stream': {
            setIsStreaming(true);
            setStreamingMessageId(msg.messageId);
            setStreamingContent(msg.fullContent);

            setMessages((prev) => {
              const exists = prev.find((m) => m.id === msg.messageId);
              if (exists) {
                return prev.map((m) =>
                  m.id === msg.messageId ? { ...m, content: msg.fullContent } : m
                );
              } else {
                return [
                  ...prev,
                  {
                    id: msg.messageId,
                    sessionId: msg.sessionId,
                    role: 'bot',
                    content: msg.fullContent,
                    createdAt: new Date().toISOString(),
                  },
                ];
              }
            });
            break;
          }

          case 'chat.done': {
            setIsStreaming(false);
            setStreamingMessageId(undefined);
            setStreamingContent('');

            setMessages((prev) =>
              prev.map((m) => (m.id === msg.message.id ? msg.message : m))
            );

            setRecentMessages((prev) => ({
              ...prev,
              [activeBotId]: msg.message.content.slice(0, 50) + '...',
            }));
            break;
          }

          case 'error': {
            console.error('[xbot-ws] server error:', msg.message);
            setIsStreaming(false);
            break;
          }
        }
      } catch (err) {
        console.error('[xbot-ws] failed to parse message:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      reconnectTimeoutRef.current = setTimeout(connect, 2000);
    };

    ws.onerror = (err) => {
      console.warn('[xbot-ws] connection error', err);
      ws.close();
    };
  }, [send, activeBotId, activeSessionId]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      socketRef.current?.close();
    };
  }, [connect]);

  // When active bot changes, switch active session and load history
  const selectBot = useCallback(
    (botId: string) => {
      setActiveBotId(botId);
      const newSessionId = `session-${botId}-initial`;
      setActiveSessionId(newSessionId);
      send({ type: 'history.get', sessionId: newSessionId });
    },
    [send]
  );

  const sendMessage = useCallback(
    (content: string) => {
      if (!content.trim() || isStreaming) return;
      send({
        type: 'chat.send',
        sessionId: activeSessionId,
        botId: activeBotId,
        content: content.trim(),
      });
    },
    [send, activeSessionId, activeBotId, isStreaming]
  );

  return {
    bots,
    activeBotId,
    activeSessionId,
    activeBot: bots.find((b) => b.id === activeBotId) || bots[0],
    messages,
    isStreaming,
    streamingMessageId,
    streamingContent,
    recentMessages,
    isConnected,
    selectBot,
    sendMessage,
  };
}
