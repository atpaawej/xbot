import { Search, Plus, Cpu, Coins, Wifi } from 'lucide-react';

interface WindowHeaderProps {
  botCount: number;
  onNewChat?: () => void;
  onOpenSearch?: () => void;
  acpConnected: boolean;
}

export const WindowHeader = ({
  botCount,
  onNewChat,
  onOpenSearch,
  acpConnected,
}: WindowHeaderProps) => {
  return (
    <header className="h-10 px-3 bg-[#0d1017] border-b border-[#1b202e] flex items-center justify-between select-none shrink-0 z-30">
      {/* Left: macOS Traffic Lights and Fleet Badge */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 group">
          <span className="w-3 h-3 rounded-full bg-[#ef4444] border border-[#dc2626]/40 inline-block transition-transform duration-100 hover:scale-110 cursor-pointer" />
          <span className="w-3 h-3 rounded-full bg-[#f59e0b] border border-[#d97706]/40 inline-block transition-transform duration-100 hover:scale-110 cursor-pointer" />
          <span className="w-3 h-3 rounded-full bg-[#10b981] border border-[#059669]/40 inline-block transition-transform duration-100 hover:scale-110 cursor-pointer" />
        </div>

        <div className="flex items-center gap-1.5 ml-1">
          <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-[#1a2030] text-blue-400 rounded-md border border-blue-900/30 tabular-nums">
            {botCount}
          </span>
          <span className="text-xs font-semibold text-zinc-400 tracking-tight">xbot fleet</span>
        </div>
      </div>

      {/* Right: Telemetry Indicators & Quick Actions */}
      <div className="flex items-center gap-4 text-xs font-medium text-zinc-400">
        {/* Telemetry metrics bar */}
        <div className="flex items-center gap-3 bg-[#131722] px-2.5 py-1 rounded-full border border-[#212738]">
          <div className="flex items-center gap-1 text-zinc-300" title="Fleet CPU / Agent Load">
            <Cpu className="w-3.5 h-3.5 text-zinc-400" />
            <span className="tabular-nums text-[11px]">46%</span>
          </div>

          <div className="w-px h-3 bg-[#242b3d]" />

          <div className="flex items-center gap-1 text-zinc-300" title="Session Fleet Ledger">
            <Coins className="w-3.5 h-3.5 text-amber-400" />
            <span className="tabular-nums text-[11px]">$4.29</span>
          </div>

          <div className="w-px h-3 bg-[#242b3d]" />

          <div className="flex items-center gap-1 text-zinc-300" title="Telemetry Mesh Health">
            <Wifi className="w-3.5 h-3.5 text-cyan-400" />
            <span className="tabular-nums text-[11px]">97%</span>
          </div>

          <div className="w-px h-3 bg-[#242b3d]" />

          <div className="flex items-center gap-1.5" title="Agent Client Protocol (ACP) Connection Status">
            <span
              className={`w-2 h-2 rounded-full ${
                acpConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
              }`}
            />
            <span className="text-[10px] font-mono tracking-wider text-emerald-400">ACP</span>
          </div>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1">
          <button
            onClick={onOpenSearch}
            className="p-1.5 text-zinc-400 hover:text-zinc-100 hover:bg-[#1a2030] rounded-lg transition-colors active:scale-95"
            title="Search conversations (⌘K)"
          >
            <Search className="w-4 h-4" />
          </button>
          <button
            onClick={onNewChat}
            className="p-1.5 text-zinc-400 hover:text-zinc-100 hover:bg-[#1a2030] rounded-lg transition-colors active:scale-95"
            title="New Session"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
