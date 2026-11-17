# {{PROJECT}}: requests inbox

Requests from one {{TERM_STUDIO}} to the owner of a shared domain (<describe the domain, e.g. "geometry: owned by the levels studio">).
The board shows this file read-only. The owner {{TERM_STUDIO}} turns each request into its own card (PROPOSED, or APPROVED when the
request carries the user's words) and writes the card ID on the request. Write only your own items; temp file + `os.replace`.

Format (sections are `## `, items are `### <ID> <title> — <tag>`, fields are `- name: text`):
```
### REQ-NN <short title> — OPEN
- from: <owner>
- where: <location / object / file>
- evidence: <picture path inside the project, or numbers>
- what: <what is wrong and what you need>
- card: <the owner's card ID once registered>
- status: open | carded <ID> | closed (why)
```

## Open

## Closed
