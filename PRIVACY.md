# Privacy Policy

**Plugin:** Function Calling Suite (`function_calling_suite`)
**Last updated:** 2026-11-24

This policy describes the data handling performed by this plugin. The Dify deployment that runs the plugin, and the model and tool providers configured in that deployment, have their own privacy policies.

## What the plugin stores

When an Agent run uses one of the three strategies, the plugin writes a conversation transcript through Dify's plugin storage API under the key:

```text
agent_transcript:{conversation_id}
```

The transcript can contain:

- the user's query text for each turn;
- assistant text responses;
- names and arguments of tool calls requested by the assistant;
- tool results returned by Dify;
- role and tool-call linkage metadata needed to replay the conversation.

If a file name or file content appears in a query or in tool output, it can therefore be part of the stored transcript.

History is scoped to the Dify conversation, not to an individual Agent node. Multiple Agent nodes using this plugin in the same conversation share one transcript.

## Purpose

The transcript is used only to replay previous turns to the model when the selected strategy has history enabled. It is not used for analytics, profiling, advertising, or training by the plugin author.

## Retention

The plugin bounds the stored transcript as follows:

- it keeps a multiple of the configured replay window: 3x `history_turns`, with a floor of 30 turns and an absolute cap of 500 turns;
- it keeps a character budget derived from `max_history_tokens_k`, with a floor of 20,000 characters and an absolute cap of 2,000,000 characters of message content;
- retention trimming uses 1.5x hysteresis, so the store can temporarily exceed a target before old whole turns are removed;
- each stored message is capped at 8,000 characters, keeping the head and tail of longer content.

Replay itself is bounded by `history_turns` and `max_history_tokens_k` for the current run. Lowering either parameter limits future replay, while the retained transcript is trimmed according to the rules above.

The plugin has no separate export or delete UI. Storage is managed by the Dify deployment. Removing the plugin's stored data is subject to the Dify deployment's plugin-storage behavior. Contact the operator of the Dify deployment for data-access or deletion requests.

## What is sent to models and tools

When a strategy has history enabled, the selected history window is included in the prompt sent to the configured model. When history is disabled, previous turns are not injected, but the current query and the current run's tool interactions are still processed normally.

Model calls and tool calls are performed through the Dify platform. The model provider and tool providers configured in the Dify deployment receive the content necessary to perform those calls, under their own policies. The plugin author does not receive this content.

## Files

Files attached to the Agent node are passed to the model through Dify; image attachments are base64-encoded into the prompt. The plugin does not persist them as separate files.

When a tool returns an image or image-link message whose text begins with `/files/`, the plugin may read that one local file and forward it to the user as a blob. This is the only local filesystem read. The plugin does not otherwise access the filesystem, and it never writes, deletes, or modifies files.

## Network access

The plugin does not make direct outbound HTTP requests and does not declare external network domains. It uses the Dify plugin APIs for model invocation, tool invocation, and storage. Network traffic to model and tool providers is initiated by Dify, not by this plugin.

## Logging

The plugin does not intentionally log message content. If persisting the transcript fails, it logs a warning that contains the conversation ID and exception details so the failure can be diagnosed.

## Permissions requested

The plugin declares the following Dify permissions:

- **Model:** invoke the model selected in the Agent node.
- **Tool:** invoke the tools supplied to the Agent node.
- **Storage:** persist transcripts, up to 200 MB.

The plugin does not request endpoint, app, or other permissions and does not contain hardcoded credentials or API keys.

## Children

The plugin is a general-purpose developer tool and is not directed at children. The operator of the Dify deployment is responsible for the content processed by it.

## Changes

If this policy changes, the updated version will be published in this repository with a new "Last updated" date.

## Contact

For privacy questions or issues, open an issue at:

https://github.com/zq393955690/function_calling_suite/issues

or email 393955690@qq.com.
