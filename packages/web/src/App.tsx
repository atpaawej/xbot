import { useState } from 'react';
import { useXbotSocket } from './hooks/useXbotSocket';
import { WindowHeader } from './components/WindowHeader';
import { Sidebar } from './components/Sidebar';
import { ChatView } from './components/ChatView';

export function App() {
  const {
    bots,
    activeBotId,
    activeBot,
    messages,
    isStreaming,
    streamingMessageId,
    streamingContent,
    recentMessages,
    isConnected,
    selectBot,
    sendMessage,
  } = useXbotSocket();

  const [userName] = useState('Aawej');

  return (
    <div className="w-screen h-screen bg-[#06080d] flex items-center justify-center p-2 sm:p-4 md:p-6 overflow-hidden">
      {/* Outer ambient glow */}
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-blue-600/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/3 w-96 h-96 bg-rose-600/5 rounded-full blur-3xl pointer-events-none" />

      {/* Main Grok Bot Style Window Shell */}
      <div className="w-full h-full max-w-7xl max-h-[960px] bg-[#0b0e15] border border-[#1d2334] rounded-2xl shadow-2xl overflow-hidden flex flex-col relative z-10">
        {/* Top Window Bar: Traffic Lights & Telemetry Header */}
        <WindowHeader
          botCount={bots.length || 7}
          acpConnected={isConnected}
          onNewChat={() => selectBot('firstmate-oss')}
          onOpenSearch={() => {}}
        />

        {/* Content Body: Sidebar + Chat Panel */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Fleet Sidebar */}
          <Sidebar
            bots={bots}
            activeBotId={activeBotId}
            onSelectBot={selectBot}
            recentMessages={recentMessages}
            userName={userName}
          />

          {/* Center / Right Chat Interface */}
          {activeBot ? (
            <ChatView
              bot={activeBot}
              messages={messages}
              isStreaming={isStreaming}
              streamingMessageId={streamingMessageId}
              streamingContent={streamingContent}
              onSendMessage={sendMessage}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-zinc-500 text-sm">
              Connecting to xbot daemon...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
