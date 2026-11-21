import type { Bot } from '@xbot/shared';
import { BotIcon } from './BotIcon';
import { LayoutGrid, Sparkles, ChevronDown } from 'lucide-react';

interface SidebarProps {
  bots: Bot[];
  activeBotId: string;
  onSelectBot: (botId: string) => void;
  recentMessages: Record<string, string>;
  userName?: string;
}

export const Sidebar = ({
  bots,
  activeBotId,
  onSelectBot,
  recentMessages,
  userName = 'Aawej',
}: SidebarProps) => {
  const activeBot = bots.find((b) => b.id === activeBotId) || bots[0];

  return (
    <aside className="w-72 bg-[#0e1119] border-r border-[#1a1f2d] flex flex-col justify-between shrink-0 select-none h-full relative">
      {/* Top Section: Active Bot Card & Fleet List */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden flex flex-col">
        {/* Active Bot Hero Card (Firstmate Squircle) */}
        {activeBot && (
          <div className="p-3 border-b border-[#181d2a]">
            <div className="p-2.5 rounded-xl bg-[#141824] border border-[#212739] flex items-center gap-3 shadow-sm hover:border-[#2d364d] transition-colors">
              <div className="relative">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-500/20 to-blue-500/20 border border-white/10 flex items-center justify-center overflow-hidden">
                  <BotIcon icon={activeBot.icon} size={24} />
                </div>
                <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 border-2 border-[#141824] rounded-full" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold text-zinc-100 truncate">
                    {activeBot.name}
                  </span>
                  <span className="text-[10px] text-zinc-500">•</span>
                  <span className="text-[10px] text-zinc-400 font-mono">ACP</span>
                </div>
                <p className="text-[11px] text-zinc-400 truncate mt-0.5">
                  {activeBot.title}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Section Header */}
        <div className="px-4 pt-3 pb-1.5 flex items-center justify-between">
          <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
            oss fleet
          </span>
          <span className="text-[10px] text-zinc-600 font-mono">
            {bots.length} bots
          </span>
        </div>

        {/* Bot List */}
        <div className="flex-1 px-2 space-y-0.5">
          {bots.map((bot) => {
            const isSelected = bot.id === activeBotId;
            const snippet =
              recentMessages[bot.id] ||
              (bot.id === 'firstmate-oss'
                ? 'I told Firstmate that the #8325 fix, #8326, is wei...'
                : bot.id === 'treehouse'
                ? '#173 is now fully green and CLEAN too (Window...'
                : bot.id === 'runner-up'
                ? 'runner-up 0.1.12 is out. I squash-merged release ...'
                : bot.id === 'no-mistakes'
                ? 'no-mistakes 1.111.0 is released. I squash-merged ...'
                : bot.id === 'gnhf'
                ? 'I released gnhf 0.1.52 by merging #249 as comm...'
                : bot.id === 'gh-axi'
                ? 'gh-axi 0.1.48 is out. I merged #244 as bb8c797...'
                : 'Audited 12 dependencies with zero vulnerability ...');

            return (
              <button
                key={bot.id}
                onClick={() => onSelectBot(bot.id)}
                className={`w-full text-left p-2 rounded-xl flex items-start gap-3 transition-all duration-150 group active:scale-[0.99] ${
                  isSelected
                    ? 'bg-[#181f2f] text-white shadow-inner border border-[#2b354d]'
                    : 'text-zinc-400 hover:bg-[#121622] hover:text-zinc-200 border border-transparent'
                }`}
              >
                <div className="mt-0.5">
                  <BotIcon icon={bot.icon} size={22} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-xs font-medium truncate ${
                        isSelected ? 'text-zinc-100 font-semibold' : 'text-zinc-300'
                      }`}
                    >
                      {bot.name}
                    </span>
                    {isSelected && (
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0 ml-1" />
                    )}
                  </div>
                  <p className="text-[11px] text-zinc-500 truncate mt-0.5 leading-snug group-hover:text-zinc-400">
                    {snippet}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        {/* Floating "More unreads" Badge */}
        <div className="p-3 flex justify-center">
          <button className="px-3 py-1 bg-blue-600/90 hover:bg-blue-600 text-white text-[11px] font-medium rounded-full shadow-lg flex items-center gap-1 transition-transform active:scale-95 border border-blue-400/30">
            <ChevronDown className="w-3.5 h-3.5" />
            <span>More unreads</span>
          </button>
        </div>
      </div>

      {/* Footer: User Profile Bar */}
      <div className="p-3 border-t border-[#181d2a] bg-[#0c0f16] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white text-xs font-bold shadow">
            {userName[0]?.toUpperCase() || 'A'}
          </div>
          <span className="text-xs font-medium text-zinc-300 truncate max-w-[120px]">
            {userName}
          </span>
        </div>

        <div className="flex items-center gap-1 text-zinc-400">
          <button
            className="p-1.5 hover:text-zinc-200 hover:bg-[#181d2a] rounded-lg transition-colors"
            title="Workspace Fleet Grid"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            className="p-1.5 hover:text-zinc-200 hover:bg-[#181d2a] rounded-lg transition-colors"
            title="Autonomous Capabilities"
          >
            <Sparkles className="w-4 h-4 text-blue-400" />
          </button>
        </div>
      </div>
    </aside>
  );
};
