---
name: gitnexus-guide
description: "Use when the user asks about GitNexus itself — available tools, how to query the knowledge graph, MCP resources, graph schema, or workflow reference. Examples: \"What GitNexus tools are available?\", \"How do I use GitNexus?\""
---

# GitNexus Guide

Quick reference for all GitNexus MCP tools, resources, and the knowledge graph schema.

## Always Start Here

For any task involving code understanding, debugging, impact analysis, or refactoring:

1. **Run `npx gitnexus status`** — check index freshness before anything else
2. **Match your task to a skill below** and **read that skill file**
3. **Follow the skill's workflow and checklist**

> If step 1 warns the index is stale, run `npx gitnexus analyze` in the terminal first.

## Skills

| Task                                         | Skill to read       |
| -------------------------------------------- | ------------------- |
| Understand architecture / "How does X work?" | `gitnexus-exploring`         |
| Blast radius / "What breaks if I change X?"  | `gitnexus-impact-analysis`   |
| Trace bugs / "Why is X failing?"             | `gitnexus-debugging`         |
| Rename / extract / split / refactor          | `gitnexus-refactoring`       |
| Tools, resources, schema reference           | `gitnexus-guide` (this file) |
| Index, status, clean, wiki CLI commands      | `gitnexus-cli`               |

## Tools Reference

| Tool             | What it gives you                                                        |
| ---------------- | ------------------------------------------------------------------------ |
| `query`          | Process-grouped code intelligence — execution flows related to a concept |
| `context`        | 360-degree symbol view — categorized refs, processes it participates in  |
| `impact`         | Symbol blast radius — what breaks at depth 1/2/3 with confidence         |
| `detect-changes` | Git-diff impact — what do your current changes affect                    |
| `cypher`         | Raw graph queries (see **Graph Schema** below)                           |
| `list`           | Discover indexed repos                                                   |

> There is **no `rename` command** in the CLI. Renaming is manual: enumerate every
> call site with `impact` / `context` / `cypher`, then edit deliberately.

## Navigation Reference (CLI)

This project runs GitNexus through the CLI only — there is no `.mcp.json`, so MCP
resources (`gitnexus://...`) and the `gitnexus_*` tools are unavailable.

| Need                       | Command                                   |
| -------------------------- | ----------------------------------------- |
| Index stats / staleness    | `npx gitnexus status`                     |
| Indexed repositories       | `npx gitnexus list`                       |
| Functional areas overview  | `npx gitnexus query "<concept>"`          |
| Execution flows            | `npx gitnexus query "<concept>" --limit N`|
| Graph schema for Cypher    | see **Graph Schema** below                |

Output format: `impact`, `context`, `query` and `cypher` print JSON; `status` and
`detect-changes` print text.

## Graph Schema

**Nodes:** File, Function, Class, Interface, Method, Community, Process
**Edges (via CodeRelation.type):** CALLS, IMPORTS, EXTENDS, IMPLEMENTS, DEFINES, MEMBER_OF, STEP_IN_PROCESS

```cypher
MATCH (caller)-[:CodeRelation {type: 'CALLS'}]->(f:Function {name: "myFunc"})
RETURN caller.name, caller.filePath
```
