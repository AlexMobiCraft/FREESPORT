---
name: gitnexus-exploring
description: "Use when the user asks how code works, wants to understand architecture, trace execution flows, or explore unfamiliar parts of the codebase. Examples: \"How does X work?\", \"What calls this function?\", \"Show me the auth flow\""
---

# Exploring Codebases with GitNexus

## When to Use

- "How does authentication work?"
- "What's the project structure?"
- "Show me the main components"
- "Where is the database logic?"
- Understanding code you haven't seen before

## Workflow

```
1. npx gitnexus list                          → Discover indexed repos
2. npx gitnexus status             → Codebase overview, check staleness
3. npx gitnexus query "<what you want to understand>"  → Find related execution flows
4. npx gitnexus context <symbol>            → Deep dive on specific symbol
5. npx gitnexus query "<flow>"      → Trace full execution flow
```

> If step 2 says "Index is stale" → run `npx gitnexus analyze` in terminal.

## Checklist

```
- [ ] npx gitnexus status
- [ ] npx gitnexus query for the concept you want to understand
- [ ] Review returned processes (execution flows)
- [ ] npx gitnexus context on key symbols for callers/callees
- [ ] READ process resource for full execution traces
- [ ] Read source files for implementation details
```

## Navigation commands (CLI)

MCP resources (`gitnexus://...`) are not available — this project has no `.mcp.json`.
Use these commands instead:

| Instead of resource | Run                                     | What you get                          |
| ------------------- | --------------------------------------- | ------------------------------------- |
| `.../context`       | `npx gitnexus status`                   | Index stats and staleness             |
| `.../clusters`      | `npx gitnexus query "<area>" --limit 10`| Functional areas by concept           |
| `.../cluster/{name}`| `npx gitnexus query "<area>" --limit 10`| Area members with file paths          |
| `.../process/{name}`| `npx gitnexus query "<flow>" --limit 1` | Execution flow with its symbols       |
| repo discovery      | `npx gitnexus list`                     | All indexed repositories              |

## Tools

**npx gitnexus query** — find execution flows related to a concept:

```
npx gitnexus query "payment processing"
→ Processes: CheckoutFlow, RefundFlow, WebhookHandler
→ Symbols grouped by flow with file locations
```

**npx gitnexus context** — 360-degree view of a symbol:

```
npx gitnexus context validateUser
→ Incoming calls: loginHandler, apiMiddleware
→ Outgoing calls: checkToken, getUserById
→ Processes: LoginFlow (step 2/5), TokenRefresh (step 1/3)
```

## Example: "How does payment processing work?"

```
1. npx gitnexus status       → 918 symbols, 45 processes
2. npx gitnexus query "payment processing"
   → CheckoutFlow: processPayment → validateCard → chargeStripe
   → RefundFlow: initiateRefund → calculateRefund → processRefund
3. npx gitnexus context processPayment
   → Incoming: checkoutHandler, webhookHandler
   → Outgoing: validateCard, chargeStripe, saveTransaction
4. Read src/payments/processor.ts for implementation details
```
