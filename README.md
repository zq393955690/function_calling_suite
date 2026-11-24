# Function Calling Suite

A Dify agent-strategy plugin that provides three native function-calling strategies with caller-controlled conversation history.

The strategies share the same model/tool loop and parameters. They differ only in how previous turns are replayed: plain Q&A text, no history, or full tool-call history. The history window is owned by the strategy rather than by Dify's built-in conversation memory.

## Strategies

| Strategy label | Internal ID | History behavior |
| --- | --- | --- |
| FunctionCalling (Q&A history) | `function_calling_text` | Replays previous user/assistant text. Tool calls and tool results are omitted. |
| FunctionCalling (no history) | `function_calling_off` | Replays no history. The transcript is still recorded for a later switch to a history-enabled strategy. |
| FunctionCalling (full history) | `function_calling_full` | Replays text, assistant tool calls, and tool results. |

## Requirements

- Dify 1.11.2 or later.
- A model that supports native function/tool calling.
- Tools supplied to the Agent node. The strategy does not bundle any tools.
- The plugin uses Dify's model invocation, tool invocation, and plugin storage APIs. No additional network connection, endpoint, or proxy configuration is required, and the plugin makes no direct outbound HTTP requests.
- The plugin forwards tool-generated images. If a tool returns an image message whose text begins with `/files/`, the plugin may read that one local file to send it to the user; it does not otherwise access the filesystem and does not write files.

## Installation

### From the Dify Marketplace

Install **Function Calling Suite** from the Dify Marketplace, then add an Agent node and select one of the three strategies from the **Function Calling Suite** provider.

### From a local package

1. Build or obtain `function_calling_suite-0.1.0.difypkg`.
2. In Dify, open **Plugins > Install Plugin > Install from local package**.
3. Upload the package and enable the plugin.

## Parameters

All three strategies expose the same parameters.

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `model` | Yes | - | Chat model used for native function calling. |
| `allowed_tools` | No | - | Optional list of tool names. When non-empty, only these tools are exposed to the model and allowed to run. |
| `tools` | Yes | - | Tool list provided by the Agent node. |
| `instruction` | Yes | - | System instruction for the agent. |
| `context` | No | - | Optional context objects supplied by the workflow. |
| `query` | Yes | - | Current user query. |
| `files` | No | - | Files attached to the current turn. |
| `history_turns` | No | `10` | Maximum number of turns replayed, range 1-100. One turn is one user message plus the assistant and tool messages that follow it. |
| `max_history_tokens_k` | No | `64` | Replay budget in thousands of tokens, range 1-200. `64` means about 64,000 tokens. This is a rough character-based estimate, not a hard cap. |
| `maximum_iterations` | No | `3` | Maximum model/tool loop iterations, range 1-500. |

In no-history mode, `history_turns` and `max_history_tokens_k` do not inject history. They only bound how much transcript is retained for a later switch to another strategy.

## How history works

### Storage

The plugin writes the transcript through Dify's plugin storage API under this key:

```text
agent_transcript:{conversation_id}
```

This means:

- History is scoped to the Dify conversation, not to an individual Agent node. Two Agent nodes using this plugin in the same conversation share one transcript.
- Transcript data stays in the Dify deployment that runs the plugin. The plugin does not send it to the plugin author or any third party.
- The plugin does not log message content. If persistence fails, it logs a warning with the conversation ID and exception details so the failure is visible.

### Retention and replay

- The stored transcript keeps a multiple of the replay window: 3x `history_turns`, with a floor of 30 turns and 500 turns as the absolute cap. It also uses a character budget derived from `max_history_tokens_k`, with a floor of 20,000 characters and a cap of 2,000,000 characters.
- Retention trimming uses 1.5x hysteresis, so the store can temporarily exceed a target before old whole turns are removed.
- A single stored message is capped at 8,000 characters. Longer content is shortened in the middle (70% head, 30% tail) before persistence.
- Replay drops whole turns from the oldest side until the requested turn count and approximate token budget fit. A single newest turn is kept even if it alone exceeds the budget.
- In Q&A text mode, assistant messages that contain tool calls are excluded together with their tool results so the model never receives orphaned tool calls.
- In no-history mode, the transcript is recorded but not injected into the model prompt.

## Compatibility and limits

- Plugin version: `0.1.0`.
- Minimum Dify version: `1.11.2`.
- Plugin runtime: Python 3.12, `amd64` and `arm64`.
- The selected model must support native function calling. JSON-mode-only or text-only models are not supported by this strategy.
- The token budget is an estimate (about 0.6 tokens per character); it is a guardrail, not an exact token count.
- Conversation history is shared across Agent nodes that use this plugin within the same conversation. Use separate conversations or a different plugin if you need per-node isolation.
- The transcript is stored only when Dify makes plugin storage available. Without storage, runs still work but no history is replayed.

## Privacy

See [PRIVACY.md](PRIVACY.md) for what the plugin stores, how long it retains data, and what is sent to models and tools.

## Contact

- Source repository: <https://github.com/zq393955690/function_calling_suite>
- Issues: <https://github.com/zq393955690/function_calling_suite/issues>
- Email: 393955690@qq.com

## License and attribution

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Portions of this plugin are derived from the LangGenius Dify official agent plugin. The derived files were modified for this project: plugin and provider identity were renamed, the strategy set was reduced to native function calling, a three-mode history implementation was added, and tool allowlist and tool-response helpers were added. Dify is a trademark of LangGenius, Inc.; this is an independent community plugin and is not affiliated with or endorsed by LangGenius.

## Development

```bash
pip install -r requirements.txt
dify plugin package .
```

The repository also includes a Chinese README at [readme/README_zh_Hans.md](readme/README_zh_Hans.md).
