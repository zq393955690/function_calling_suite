"""History building for the custom function-calling strategy.

The platform's built-in memory is deliberately not used: this module owns the
window (counted in turns), the token budget and the shape of the replay.
Entries are plain dicts so they survive JSON round-trips in ``session.storage``:

    {"role": "user", "content": "..."}
    {"role": "assistant", "content": "", "tool_calls": [
        {"id": "call_1", "function": {"name": "search", "arguments": "{}"}}]}
    {"role": "tool", "tool_call_id": "call_1", "name": "search", "content": "..."}
"""

from __future__ import annotations

import json
from typing import Any

from dify_plugin.entities.model.message import (
    AssistantPromptMessage,
    SystemPromptMessage,
    ToolPromptMessage,
    UserPromptMessage,
)

KEY_PREFIX = "agent_transcript"

MAX_MESSAGE_CHARS = 8000
KEEP_TURNS_FACTOR = 3
KEEP_CHARS_FACTOR = 5
KEEP_TURNS_CAP = 500
KEEP_CHARS_CAP = 2_000_000
HYSTERESIS = 1.5


def truncate_long_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cap a single oversized message before it is persisted.

    The read-side budget can never drop a turn that is itself larger than the
    whole budget, so the guard has to happen at write time. Head-heavy split:
    conclusions and totals usually sit at the tail end of tool output.
    """
    for message in messages:
        content = message.get("content")
        if isinstance(content, str) and len(content) > MAX_MESSAGE_CHARS:
            head = int(MAX_MESSAGE_CHARS * 0.7)
            tail = MAX_MESSAGE_CHARS - head
            message["content"] = (
                content[:head]
                + f"\n...[truncated, {len(content)} chars total]...\n"
                + content[-tail:]
            )
    return messages


def _trim_for_storage(
    messages: list[dict[str, Any]],
    keep_turns: int,
    keep_chars: int,
) -> list[dict[str, Any]]:
    positions = _user_positions(messages)

    def total_chars() -> int:
        return sum(len(str(m.get("content") or "")) for m in messages)

    # Hysteresis: leave the history alone until it clearly outgrows the budget,
    # so lowering the window does not wipe history on the very next turn.
    if len(positions) <= keep_turns * HYSTERESIS and total_chars() <= keep_chars * HYSTERESIS:
        return messages

    while positions and (len(positions) > keep_turns or total_chars() > keep_chars):
        if len(positions) <= 1:
            break
        messages = messages[positions[1]:]
        positions = _user_positions(messages)

    return messages

# 中文约 1 字 1 token，英文约 3.5 字符 1 token，取 0.6 作折中系数。
_TOKENS_PER_CHAR = 0.6


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough token estimate; good enough to bound the history block."""
    total = 0
    for message in messages:
        content = message.get("content") or ""
        if isinstance(content, str):
            total += int(len(content) * _TOKENS_PER_CHAR) + 4
        for call in message.get("tool_calls") or []:
            arguments = (call.get("function") or {}).get("arguments") or ""
            total += int(len(str(arguments)) * _TOKENS_PER_CHAR) + 8
    return total


def _user_positions(messages: list[dict[str, Any]]) -> list[int]:
    return [
        index for index, message in enumerate(messages) if message.get("role") == "user"
    ]


def trim_turns(messages: list[dict[str, Any]], turns: int) -> list[dict[str, Any]]:
    """Keep the newest ``turns`` turns, counted from ``user`` boundaries."""
    if turns <= 0:
        return []
    positions = _user_positions(messages)
    if len(positions) <= turns:
        return messages
    return messages[positions[-turns]:]


def trim_budget(
    messages: list[dict[str, Any]], max_tokens: int
) -> list[dict[str, Any]]:
    """Drop whole turns from the oldest side until the budget fits."""
    while messages and estimate_tokens(messages) > max_tokens:
        positions = _user_positions(messages)
        if len(positions) <= 1:
            break
        messages = messages[positions[1]:]
    return messages


def ensure_user_first(
    messages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Some providers reject a history that starts with an assistant message."""
    for index, message in enumerate(messages):
        if message.get("role") == "user":
            return messages[index:]
    return []


def to_prompt_messages(messages: list[dict[str, Any]]) -> list[Any]:
    prompt_messages: list[Any] = []
    for message in messages:
        role = (message.get("role") or "").lower()
        content = message.get("content") or ""

        if role == "user":
            prompt_messages.append(UserPromptMessage(content=content))
        elif role == "assistant":
            calls = message.get("tool_calls") or []
            if not calls:
                prompt_messages.append(AssistantPromptMessage(content=content))
                continue
            tool_calls = [
                AssistantPromptMessage.ToolCall(
                    id=call.get("id") or f"call_{index}",
                    type="function",
                    function=AssistantPromptMessage.ToolCall.ToolCallFunction(
                        name=(call.get("function") or {}).get("name") or "tool",
                        arguments=(call.get("function") or {}).get("arguments") or "{}",
                    ),
                )
                for index, call in enumerate(calls)
            ]
            prompt_messages.append(
                AssistantPromptMessage(content=content, tool_calls=tool_calls)
            )
        elif role == "tool":
            prompt_messages.append(
                ToolPromptMessage(
                    content=content,
                    tool_call_id=message.get("tool_call_id") or "",
                    name=message.get("name") or "tool",
                )
            )
    return prompt_messages


def build_history(
    *,
    system_message: SystemPromptMessage,
    messages: list[dict[str, Any]],
    mode: str,
    turns: int,
    max_tokens: int,
) -> list[Any]:
    """Assemble the leading messages (system + replayed history)."""
    if mode == "off":
        return [system_message]

    if mode != "full":
        # text 模式：只留纯文本问答。带 tool_calls 的 assistant 必须一起丢掉，
        # 否则会留下没有 tool 结果应答的孤儿调用，provider 直接报错。
        messages = [
            m
            for m in messages
            if m.get("role") == "user"
            or (m.get("role") == "assistant" and not m.get("tool_calls"))
        ]

    messages = trim_turns(messages, turns)
    messages = trim_budget(messages, max_tokens)
    messages = ensure_user_first(messages)

    return [system_message, *to_prompt_messages(messages)]


class TranscriptStore:
    """Per-conversation transcript in the plugin's persistent key-value store."""

    def __init__(self, storage: Any, conversation_id: str) -> None:
        self._storage = storage
        self._key = f"{KEY_PREFIX}:{conversation_id}"

    def load(self) -> list[dict[str, Any]]:
        if self._storage is None:
            return []
        try:
            raw = self._storage.get(self._key)
        except Exception:
            return []
        if not raw:
            return []
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return []
        return data if isinstance(data, list) else []

    def save(
        self,
        messages: list[dict[str, Any]],
        *,
        history_turns: int = 10,
        max_history_tokens: int = 64000,
    ) -> None:
        """Persist the transcript, bounded by the configured window.

        Storage keeps a multiple of the window so a later increase still has
        material to work with, but never more than the absolute caps.
        """
        if self._storage is None:
            return

        messages = truncate_long_messages(messages)

        keep_turns = min(max(history_turns * KEEP_TURNS_FACTOR, 30), KEEP_TURNS_CAP)
        keep_chars = min(
            max(max_history_tokens * KEEP_CHARS_FACTOR, 20_000), KEEP_CHARS_CAP
        )
        messages = _trim_for_storage(messages, keep_turns, keep_chars)

        try:
            self._storage.set(
                self._key, json.dumps(messages, ensure_ascii=False).encode("utf-8")
            )
        except Exception:
            # Storage quota exhausted or backend error: keep the run alive, but
            # never fail silently in the logs.
            import logging

            logging.getLogger(__name__).warning(
                "failed to persist transcript for conversation %s",
                self._key.split(":", 1)[-1],
                exc_info=True,
            )

    def clear(self) -> None:
        if self._storage is None:
            return
        try:
            self._storage.delete(self._key)
        except Exception:
            pass
