"""Tools registry for xbot agent."""

from xbot.tools.bash import bash
from xbot.tools.file_tools import edit, glob, grep, read, write
from xbot.tools.web_tools import web_fetch, web_search

# All 8 core tools
ALL_TOOLS = [
    bash,
    write,
    edit,
    read,
    grep,
    glob,
    web_search,
    web_fetch,
]

TOOL_METADATA = {
    "bash": "Execute shell commands in the workspace environment",
    "write": "Create or overwrite files with specified content",
    "edit": "Search and replace exact content blocks in existing files",
    "read": "Read file contents with line numbering and optional range slicing",
    "grep": "Search for regex or text patterns across files",
    "glob": "Find files matching wildcard paths",
    "web_search": "Search live web via TinyFish Web Search API",
    "web_fetch": "Extract clean markdown/text from URLs via TinyFish Web Fetch API",
}

__all__ = [
    "ALL_TOOLS",
    "TOOL_METADATA",
    "bash",
    "write",
    "edit",
    "read",
    "grep",
    "glob",
    "web_search",
    "web_fetch",
]
