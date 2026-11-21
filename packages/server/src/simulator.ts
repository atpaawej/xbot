import type { Bot } from '@xbot/shared';

export interface StreamChunk {
  delta: string;
  fullContent: string;
}

export async function* simulateBotStream(
  prompt: string,
  bot: Bot,
  options: { chunkDelayMs?: number } = {}
): AsyncGenerator<StreamChunk> {
  const delayMs = options.chunkDelayMs ?? 25;

  const responseText = generateSimulatedResponse(prompt, bot);
  const words = responseText.split(/(\s+)/);

  let fullContent = '';
  for (const word of words) {
    fullContent += word;
    yield {
      delta: word,
      fullContent,
    };
    if (delayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
}

function generateSimulatedResponse(prompt: string, bot: Bot): string {
  const lower = prompt.toLowerCase();

  if (lower.includes('issue') || lower.includes('pr') || lower.includes('triage') || lower.includes('fleet')) {
    return `Checking the fleet's records now, captain.

Captain, here is the current triage status across all connected repositories:
- **Active Pull Requests**: 14 pending review, 6 ready to merge
- **Unresolved Issues**: 28 open (3 marked \`needs-triage\`, 5 marked \`ready-for-agent\`)
- **Fleet Workspaces**: All 7 bots are synchronized and operational

All routine health checks are passing cleanly. Would you like me to inspect any specific workspace or trigger an automated review routine?`;
  }

  if (lower.includes('status') || lower.includes('health') || lower.includes('ping')) {
    return `**${bot.title}** status report:
- **Bot State**: Online & Ready
- **Harness**: \`${bot.harnessCommand}\` via Agent Client Protocol (ACP)
- **Workspace**: \`${bot.workspacePath}\`
- **Memory**: \`MEMORY.md\` indexed with 0 pending approvals

I am standing by for autonomous directives or routine triggers.`;
  }

  if (lower.includes('test') || lower.includes('build') || lower.includes('ci')) {
    return `Running targeted verification routine for **${bot.name}**...

\`\`\`bash
$ pnpm test
✔ DatabaseSync: tables initialized and seeded
✔ WebSocket: chat stream broadcast verified
✔ Persistence: conversation restored on reconnect
All 7/7 prove-it assertions green (0ms jitter).
\`\`\`

The workspace build is completely clean. Ready for the next instruction.`;
  }

  return `Acknowledged, captain.

I have processed your request:
> "${prompt}"

As **${bot.title}**, I am ready to carry out this workflow within \`${bot.workspacePath}\`. Once full ACP execution is activated in Ticket #3, I will dispatch tool calls through our sandboxed harness and report live file diffs and command outputs here.`;
}
