---
name: gitnexus-debugging
description: "Use when the user is debugging a bug, tracing an error, or asking why something fails. Examples: \"Why is X failing?\", \"Where does this error come from?\", \"Trace this bug\""
---

# Debugging with GitNexus

## When to Use

- "Why is this function failing?"
- "Trace where this error comes from"
- "Who calls this method?"
- "This endpoint returns 500"
- Investigating bugs, errors, or unexpected behavior

## Workflow

```
1. npx gitnexus query "<error or symptom>"            → Find related execution flows
2. npx gitnexus context <suspect>                    → See callers/callees/processes
3. npx gitnexus query "<flow>"                → Trace execution flow
4. npx gitnexus cypher "MATCH path..."                 → Custom traces if needed
```

> If "Index is stale" → run `npx gitnexus analyze` in terminal.

## Checklist

```
- [ ] Understand the symptom (error message, unexpected behavior)
- [ ] npx gitnexus query for error text or related code
- [ ] Identify the suspect function from returned processes
- [ ] npx gitnexus context to see callers and callees
- [ ] Trace execution flow via process resource if applicable
- [ ] npx gitnexus cypher for custom call chain traces if needed
- [ ] Read source files to confirm root cause
```

## Debugging Patterns

| Symptom              | GitNexus Approach                                          |
| -------------------- | ---------------------------------------------------------- |
| Error message        | `npx gitnexus query` for error text → `context` on throw sites |
| Wrong return value   | `context` on the function → trace callees for data flow    |
| Intermittent failure | `context` → look for external calls, async deps            |
| Performance issue    | `context` → find symbols with many callers (hot paths)     |
| Recent regression    | `detect-changes` to see what your changes affect           |

## Tools

**npx gitnexus query** — find code related to error:

```
npx gitnexus query "payment validation error"
→ Processes: CheckoutFlow, ErrorHandling
→ Symbols: validatePayment, handlePaymentError, PaymentException
```

**npx gitnexus context** — full context for a suspect:

```
npx gitnexus context validatePayment
→ Incoming calls: processCheckout, webhookHandler
→ Outgoing calls: verifyCard, fetchRates (external API!)
→ Processes: CheckoutFlow (step 3/7)
```

**npx gitnexus cypher** — custom call chain traces:

```cypher
MATCH path = (a)-[:CodeRelation {type: 'CALLS'}*1..2]->(b:Function {name: "validatePayment"})
RETURN [n IN nodes(path) | n.name] AS chain
```

## Example: "Payment endpoint returns 500 intermittently"

```
1. npx gitnexus query "payment error handling"
   → Processes: CheckoutFlow, ErrorHandling
   → Symbols: validatePayment, handlePaymentError

2. npx gitnexus context validatePayment
   → Outgoing calls: verifyCard, fetchRates (external API!)

3. npx gitnexus query "CheckoutFlow"
   → Step 3: validatePayment → calls fetchRates (external)

4. Root cause: fetchRates calls external API without proper timeout
```
