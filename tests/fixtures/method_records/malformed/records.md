# Parser fixture

| ID | Traces | Statement |
|---|---|---|
| DEC-001 | VO-001 | first valid record |
| DEC-002 | VO-001 |
| DEC-003 | DEC-001, DEC-002 | parsing continues |

```markdown
| ID | Traces | Statement |
|---|---|---|
| DEC-999 | VO-999 | fenced example, not a record |
```

| ID | Traces | Statement |
|---|---|---|
| DEC-004 | DEC-002, DEC-003 | final valid record |
