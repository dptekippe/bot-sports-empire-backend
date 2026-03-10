---
name: failure-mode-docs
description: "Document what breaks and how to recover"
---

# Failure Mode Documentation

## Purpose

Document what fails and how to recover. Build a knowledge base of problems and solutions.

## What to Document

| When | Document |
|------|----------|
| Something breaks | What happened |
| Fix it | How you fixed it |
| Recover | Steps to recover |
| Learn | What to do differently |

## Format

```
## Failure: [What broke]

### Symptoms
- Observable error
- What user saw

### Cause
- Root cause

### Recovery
- Steps to fix

### Prevention
- How to avoid this in future
```

## Example

```
## Failure: Token bleed from cron

### Symptoms
- 2.8M tokens in one hour
- MiniMax rate limit hit
- Context growing unbounded

### Cause
- 5-minute cron jobs
- Session log reading

### Recovery
- Delete crons: crontab -r
- Disable session reading
- Install Lossless Claw

### Prevention
- No automated API calls
- Always use Lossless Claw
- Monitor token usage
```

## When to Update

- After any failure
- After any recovery
- When you learn something new

## Key Principle

**Failures are learning opportunities. Document them.**
