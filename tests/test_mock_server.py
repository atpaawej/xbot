"""Integration test simulating an OpenAI-compatible server."""

import asyncio
import json
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import pytest
from xbot.config import Config
from xbot.agent import AgentManager, AgentTextDelta, AgentToolStart, AgentToolEnd, AgentToolResult


def get_free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class MockOpenAIHandler(BaseHTTPRequestHandler):
    turn = 0

    def do_POST(self):
        if self.path.endswith("/chat/completions"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            MockOpenAIHandler.turn += 1

            if MockOpenAIHandler.turn == 1:
                # First turn: model decides to call glob tool
                chunk1 = {
                    "id": "chatcmpl-1",
                    "object": "chat.completion.chunk",
                    "created": 1234567,
                    "model": "mock-model",
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "tool_calls": [{
                                "index": 0,
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "glob",
                                    "arguments": '{"pattern": "*.txt"}'
                                }
                            }]
                        },
                        "finish_reason": None
                    }]
                }
                chunk2 = {
                    "id": "chatcmpl-1",
                    "object": "chat.completion.chunk",
                    "created": 1234567,
                    "model": "mock-model",
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "tool_calls"
                    }]
                }
                self.wfile.write(f"data: {json.dumps(chunk1)}\n\n".encode())
                self.wfile.write(f"data: {json.dumps(chunk2)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()

            else:
                # Second turn after tool result: final answer
                chunk1 = {
                    "id": "chatcmpl-2",
                    "object": "chat.completion.chunk",
                    "created": 1234567,
                    "model": "mock-model",
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "content": "I found your files!"
                        },
                        "finish_reason": None
                    }]
                }
                chunk2 = {
                    "id": "chatcmpl-2",
                    "object": "chat.completion.chunk",
                    "created": 1234567,
                    "model": "mock-model",
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                self.wfile.write(f"data: {json.dumps(chunk1)}\n\n".encode())
                self.wfile.write(f"data: {json.dumps(chunk2)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


@pytest.mark.asyncio
async def test_agent_full_tool_execution_flow(tmp_path):
    """Test full agent loop: user -> model -> tool call -> tool result -> final answer."""
    # Create sample file for glob
    (tmp_path / "hello.txt").write_text("sample content")

    port = get_free_port()
    MockOpenAIHandler.turn = 0
    server = HTTPServer(("127.0.0.1", port), MockOpenAIHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        cfg = Config(
            base_url=f"http://127.0.0.1:{port}/v1",
            api_key="sk-mock-key",
            model_id="mock-model",
            tinyfish_api_key="",
            workspace_dir=tmp_path,
            bash_timeout=10,
            temperature=0.0,
            loaded_env_files=[],
        )
        manager = AgentManager(config=cfg)

        events_received = []
        async for ev in manager.stream_turn("Find all txt files"):
            events_received.append(ev)

        # Verify tool call was emitted
        tool_starts = [e for e in events_received if isinstance(e, AgentToolStart)]
        assert len(tool_starts) == 1
        assert tool_starts[0].tool_name == "glob"

        tool_results = [e for e in events_received if isinstance(e, AgentToolResult)]
        assert len(tool_results) == 1
        assert "hello.txt" in tool_results[0].result

        # Verify final text delta
        text_deltas = [e for e in events_received if isinstance(e, AgentTextDelta)]
        full_text = "".join(d.chunk for d in text_deltas)
        assert "I found your files!" in full_text

    finally:
        server.shutdown()
        server.server_close()
