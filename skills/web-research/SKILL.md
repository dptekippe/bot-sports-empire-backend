---
name: web-research
description: Web research using Perplexity Sonar for accurate, cited answers. Use when you need to gather current information, verify facts, or learn about topics. Triggered by: "search", "research", "find information", "look up", "what is", "how does", "latest news", or when you need to confirm something with web sources.
---

# Web Research

Use the `web_search` tool for accurate, cited answers from the web.

## When to Use

- When you need current information
- When facts need verification
- When learning about a new topic
- When the user asks "what is", "how does", "why does"
- When you need citations or sources

## Tool Usage

```javascript
web_search({
  query: "your search question",
  count: 5,        // number of results (1-10)
  freshness: "pd"  // pd (past day), pw (past week), pm (past month), py (past year)
})
```

## Examples

**Quick fact check:**
```
web_search({ query: "DynastyDroid platform features", count: 3 })
```

**Latest news:**
```
web_search({ query: "NFL draft 2026 trends", freshness: "pw", count: 5 })
```

**Research topic:**
```
web_search({ query: "best practices for fantasy football drafting", count: 10 })
```

## Tips

- Always cite sources in your response
- Use `freshness: "pd"` for time-sensitive topics
- Use `count: 5-10` for thorough research
- Follow up with `web_fetch` if you need to extract content from specific URLs
