import { useState, useRef, useEffect } from 'react';
import type { Bot, Message } from '@xbot/shared';
import {
  Plus,
  Mic,
  ArrowUp,
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  RotateCw,
  MoreHorizontal,
} from 'lucide-react';

interface ChatViewProps {
  bot: Bot;
  messages: Message[];
  isStreaming: boolean;
  streamingMessageId?: string;
  streamingContent?: string;
  onSendMessage: (text: string) => void;
}

export const ChatView = ({
  bot,
  messages,
  isStreaming,
  streamingMessageId,
  streamingContent,
  onSendMessage,
}: ChatViewProps) => {
  const [inputText, setInputText] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages or streaming tokens
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputText.trim() || isStreaming) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0a0c12] relative overflow-hidden">
      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-12 lg:px-20 space-y-6">
        {/* Date Divider */}
        <div className="flex items-center justify-center my-2">
          <span className="text-[11px] font-medium text-zinc-500 bg-[#10141e] px-3 py-1 rounded-full border border-[#1b2130]">
            Today 2:31 PM
          </span>
        </div>

        {/* Message Thread */}
        {messages.map((msg, index) => {
          const isUser = msg.role === 'user';
          const isCurrentStreaming = isStreaming && msg.id === streamingMessageId;
          const displayContent = isCurrentStreaming ? streamingContent || msg.content : msg.content;

          return (
            <div
              key={msg.id || index}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} group`}
            >
              {/* Message Bubble */}
              {isUser ? (
                <div className="max-w-[85%] md:max-w-[70%] bg-[#1a2130] text-zinc-100 px-4 py-2.5 rounded-2xl rounded-tr-sm border border-[#273249] shadow-sm text-sm leading-relaxed break-words">
                  {displayContent}
                </div>
              ) : (
                <div className="w-full max-w-[90%] md:max-w-[82%] text-zinc-200 text-sm leading-relaxed space-y-3">
                  {/* Rich rendered text content */}
                  <div className="whitespace-pre-wrap font-sans text-zinc-200 select-text leading-relaxed">
                    {displayContent}
                    {isCurrentStreaming && (
                      <span className="inline-block w-1.5 h-4 bg-blue-400 ml-1 translate-y-0.5 animate-pulse" />
                    )}
                  </div>

                  {/* Grok Bot Action Bar */}
                  <div className="flex items-center gap-2 pt-1 text-zinc-500 opacity-90 transition-opacity">
                    <button
                      onClick={() => handleCopy(msg.id, displayContent)}
                      className="p-1 hover:text-zinc-200 hover:bg-[#151926] rounded-md transition-colors"
                      title="Copy response"
                    >
                      {copiedId === msg.id ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                    <button
                      className="p-1 hover:text-zinc-200 hover:bg-[#151926] rounded-md transition-colors"
                      title="Good response"
                    >
                      <ThumbsUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      className="p-1 hover:text-zinc-200 hover:bg-[#151926] rounded-md transition-colors"
                      title="Needs improvement"
                    >
                      <ThumbsDown className="w-3.5 h-3.5" />
                    </button>
                    <button
                      className="p-1 hover:text-zinc-200 hover:bg-[#151926] rounded-md transition-colors"
                      title="Regenerate"
                    >
                      <RotateCw className="w-3.5 h-3.5" />
                    </button>
                    <button
                      className="p-1 hover:text-zinc-200 hover:bg-[#151926] rounded-md transition-colors"
                      title="More actions"
                    >
                      <MoreHorizontal className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Message Source Footer Tag */}
        <div className="flex items-center justify-center pt-2">
          <span className="text-[11px] text-zinc-500 flex items-center gap-1">
            Message from <strong className="text-zinc-400 font-medium">{bot.name}</strong> ↓
          </span>
        </div>

        <div ref={messagesEndRef} className="h-20" />
      </div>

      {/* Floating Pill Input Bar */}
      <div className="absolute bottom-5 inset-x-0 flex justify-center px-4 pointer-events-none z-20">
        <form
          onSubmit={handleSubmit}
          className="w-full max-w-2xl bg-[#121622]/95 border border-[#21293c] shadow-2xl backdrop-blur-md rounded-full px-3.5 py-2 flex items-center gap-2 pointer-events-auto transition-all focus-within:border-blue-500/60 focus-within:ring-2 focus-within:ring-blue-500/20"
        >
          {/* Plus action button */}
          <button
            type="button"
            className="w-7 h-7 rounded-full bg-[#1b2131] hover:bg-[#252d43] text-zinc-400 hover:text-zinc-200 flex items-center justify-center shrink-0 transition-colors active:scale-95"
            title="Attach skill, tool, or connector"
          >
            <Plus className="w-4 h-4" />
          </button>

          {/* Text Input */}
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
            placeholder="Type your answer, or talk about something else"
            className="flex-1 bg-transparent border-none outline-none text-zinc-100 placeholder-zinc-500 text-sm py-1 px-1 disabled:opacity-60"
          />

          {/* Microphone Icon Button */}
          <button
            type="button"
            className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-[#1b2131] rounded-full transition-colors active:scale-95"
            title="Voice mode"
          >
            <Mic className="w-4 h-4" />
          </button>

          {/* Send Button with glowing xbot arrow */}
          <button
            type="submit"
            disabled={!inputText.trim() || isStreaming}
            className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-all active:scale-90 ${
              inputText.trim() && !isStreaming
                ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-md shadow-blue-500/30'
                : 'bg-[#1a2030] text-zinc-500 cursor-not-allowed'
            }`}
            title="Send prompt"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
