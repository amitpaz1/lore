# Story 9: MCP Server

**Batch:** 8 | **Est:** 3-4h | **Dependencies:** Story 6

## Description

Implement an MCP (Model Context Protocol) server that exposes Lore operations as tools. Any MCP-compatible client (Claude Desktop, OpenClaw, etc.) can use Lore for agent memory with zero code. The MCP server is a thin wrapper around the existing Lore SDK.

## Acceptance Criteria

1. `lore mcp` CLI command starts an MCP server using stdio transport
2. Server exposes `save_lesson` tool: params (problem, resolution, context?, tags?, project?) → calls `lore.publish()`
3. Server exposes `recall_lessons` tool: params (query, tags?, project?, limit?) → calls `lore.query()`, returns formatted lessons
4. Server exposes `upvote_lesson` tool: params (lesson_id) → calls `lore.upvote()`
5. Server exposes `downvote_lesson` tool: params (lesson_id) → calls `lore.downvote()`
6. Store selection via env vars: `LORE_STORE=local` (default, SqliteStore) or `LORE_STORE=remote` (RemoteStore using `LORE_API_URL` + `LORE_API_KEY`)
7. `LORE_PROJECT` env var sets default project for all operations
8. Tool descriptions include clear guidance for LLMs on when to use each tool
9. Works with Claude Desktop config (add to `mcpServers` in config JSON)
10. `save_lesson` returns confirmation with lesson ID
11. `recall_lessons` returns lessons formatted as readable text (not raw JSON)
12. Errors return human-readable error messages (not stack traces)

## Technical Notes

- File: `src/lore/mcp/server.py`
- Add `mcp` as optional dependency: `pip install lore-memory[mcp]`
- Use `mcp` Python SDK for stdio transport and tool registration
- The MCP server creates a `Lore` instance on startup based on env vars
- ~200 lines of code — it's a thin wrapper
- Add `mcp` subcommand to `src/lore/cli.py`
- Tool descriptions are critical — they tell the LLM WHEN to save vs recall
