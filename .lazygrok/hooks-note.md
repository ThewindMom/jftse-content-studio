# LazyGrok hooks note (project)

Codegraph was removed from LazyGrok plugin hooks and MCP for this workspace preference:

- `SessionStart` codegraph bootstrap hook removed
- `PostToolUse` codegraph matcher removed  
- `lazygrok-codegraph` MCP server removed from plugin `.mcp.json`

Location of edits: `~/.grok/installed-plugins/lazygrok-*/hooks/hooks.json` and `.mcp.json`.

Restart Grok sessions to drop any already-connected codegraph MCP process.
