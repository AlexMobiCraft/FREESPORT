---
name: gitnexus-refactoring
description: "Use when the user wants to rename, extract, split, move, or restructure code safely. Examples: \"Rename this function\", \"Extract this into a module\", \"Refactor this class\", \"Move this to a separate file\""
---

# Refactoring with GitNexus

## When to Use

- "Rename this function safely"
- "Extract this into a module"
- "Split this service"
- "Move this to a new file"
- Any task involving renaming, extracting, splitting, or restructuring code

## Workflow

```
1. npx gitnexus impact X --direction upstream  → Map all dependents
2. npx gitnexus query "X"                            → Find execution flows involving X
3. npx gitnexus context X                           → See all incoming/outgoing refs
4. Plan update order: interfaces → implementations → callers → tests
```

> If "Index is stale" → run `npx gitnexus analyze` in terminal.

## Checklists

### Rename Symbol

> **There is no `rename` command in the CLI.** Renaming is manual — but never a blind
> find-and-replace. Build the exhaustive call-site list from the graph first.

```
- [ ] npx gitnexus impact oldName --direction upstream --include-tests — every dependent
- [ ] npx gitnexus context oldName — incoming/outgoing refs and the file that defines it
- [ ] npx gitnexus cypher "MATCH (c)-[:CodeRelation {type: 'CALLS'}]->(f {name: 'oldName'}) RETURN c.name, c.filePath"
- [ ] Grep for dynamic/string references the graph cannot see (configs, templates, serializers)
- [ ] Edit definition first, then callers, then tests — one file at a time
- [ ] npx gitnexus detect-changes --scope all — verify only expected files changed
- [ ] Run tests for affected processes
- [ ] npx gitnexus analyze — reindex, or the graph keeps returning the old name
```

### Extract Module

```
- [ ] npx gitnexus context <symbol> — see all incoming/outgoing refs
- [ ] npx gitnexus impact <symbol> --direction upstream — find all external callers
- [ ] Define new module interface
- [ ] Extract code, update imports
- [ ] npx gitnexus detect-changes — verify affected scope
- [ ] Run tests for affected processes
```

### Split Function/Service

```
- [ ] npx gitnexus context <symbol> — understand all callees
- [ ] Group callees by responsibility
- [ ] npx gitnexus impact <symbol> --direction upstream — map callers to update
- [ ] Create new functions/services
- [ ] Update callers
- [ ] npx gitnexus detect-changes — verify affected scope
- [ ] Run tests for affected processes
```

## Tools

**npx gitnexus cypher** — enumerate call sites for a manual rename:

```
npx gitnexus cypher "MATCH (c)-[:CodeRelation {type: 'CALLS'}]->(f {name: 'validateUser'}) RETURN c.name, c.filePath"
→ {"markdown": "| c.name | c.filePath |\n| --- | --- |\n| loginHandler | src/auth/login.ts |", "row_count": 1}
```

The graph sees static references only. Dynamic ones — names in config files, string-based
dispatch, serializer field maps — must still be found with grep.

**npx gitnexus impact** — map all dependents first:

```
npx gitnexus impact validateUser --direction upstream
→ d=1: loginHandler, apiMiddleware, testUtils
→ Affected Processes: LoginFlow, TokenRefresh
```

**npx gitnexus detect-changes** — verify your changes after refactoring:

```
npx gitnexus detect-changes --scope all
→ Changed: 8 files, 12 symbols
→ Affected processes: LoginFlow, TokenRefresh
→ Risk: MEDIUM
```

**npx gitnexus cypher** — custom reference queries:

```cypher
MATCH (caller)-[:CodeRelation {type: 'CALLS'}]->(f:Function {name: "validateUser"})
RETURN caller.name, caller.filePath ORDER BY caller.filePath
```

## Risk Rules

| Risk Factor         | Mitigation                                |
| ------------------- | ----------------------------------------- |
| Many callers (>5)   | Enumerate with `impact --include-tests`, edit file by file |
| Cross-area refs     | Use detect-changes after to verify scope  |
| String/dynamic refs | npx gitnexus query to find them               |
| External/public API | Version and deprecate properly            |

## Example: Rename `validateUser` to `authenticateUser`

```
1. npx gitnexus impact validateUser --direction upstream --include-tests
   → d=1: loginHandler, apiMiddleware, testUtils
   → Affected Processes: LoginFlow, TokenRefresh
   → risk: MEDIUM

2. npx gitnexus cypher "MATCH (c)-[:CodeRelation {type: 'CALLS'}]->(f {name: 'validateUser'}) RETURN c.name, c.filePath"
   → exact file list to edit

3. grep -rn "validateUser" --include=*.json --include=*.yaml
   → config.json: dynamic reference the graph cannot see

4. Edit definition → callers → tests, one file at a time

5. npx gitnexus detect-changes --scope all
   → Affected: LoginFlow, TokenRefresh
   → Risk: MEDIUM — run tests for these flows

6. npx gitnexus analyze
   → reindex, otherwise the graph still answers for the old name
```
