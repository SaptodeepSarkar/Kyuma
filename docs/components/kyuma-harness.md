# Kyuma Harness (moderator)

Terminal app that spawns all helpers, starts services, owns the decision loop.
Status UI in QuickShell; core stays terminal.

- Input: streaming words from STT.
- Buffers fragments in an ARRAY until a full command/sentence forms.
- Sends complete sentences to the Model Manager API, waits for response.
- Converts response to exec code, forwards to Implementation Harness.
- Flushes the buffer on 200 or error, then keeps listening.
- Never blocks speech on action.
