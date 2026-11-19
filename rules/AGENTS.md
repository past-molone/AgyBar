# AgyBar Planning Protocol

You are equipped with the **AgyBar Progress Tracking System**. To give the user real-time visual progress of your execution, follow these guidelines:

## 1. Plan First (Required for Multi-Step Tasks)
Before executing multiple tool calls or non-trivial modifications, formulate a high-level plan and declare it at the start of your turn.

Use either the structured XML tag (preferred) or standard bracketed step notation:

### Preferred (Structured Tag):
```html
<!-- agybar:plan {"total": 4, "steps": ["Analyze codebase", "Implement solution", "Run test suite", "Verify and document"]} -->
```

### Alternative (Text Notation):
```markdown
[Step 1/4: Analyze codebase]
```

## 2. Milestone Updates
When you advance to subsequent steps, update the active milestone:

```html
<!-- agybar:step {"current": 2, "name": "Implement solution"} -->
```
or write:
```markdown
[Step 2/4: Implement solution]
```

## 3. Keep Descriptions Concise
Keep step names short (under 40 characters) so they display cleanly on the user's terminal status line.
