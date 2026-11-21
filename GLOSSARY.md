# xbot

An open-source Grok Bot alternative providing persistent, autonomous AI agents capable of multi-step workflows across tools and schedules.

## Language

**Bot**:
A persistent, autonomous AI agent with dedicated context, memory, and tool access.
_Avoid_: Agent, worker, assistant

**Skill**:
A reusable instruction set defining inputs, step sequences, decision rules, and expected outputs for a task.
_Avoid_: Task, workflow, macro

**Routine**:
A trigger configuration that executes a Bot or Skill on a schedule or in response to an external event.
_Avoid_: Cron, job, automation

**Connector**:
An integration bridging external services, platforms, or APIs into the Bot's environment.
_Avoid_: Plugin, integration, adapter

**Approval Gate**:
A human-in-the-loop checkpoint that pauses execution before a high-consequence action until approved.
_Avoid_: Confirmation prompt, review step
