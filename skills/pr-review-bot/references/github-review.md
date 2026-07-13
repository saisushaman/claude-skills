# Posting an inline GitHub review (exact mechanics)

Validated against `your-org/<repo-a>` PRs #16 and #20.

## 1. Anchor to the head commit
Inline comments must reference lines in the PR's **head** revision, not the diff
hunk numbers.

```
gh pr view <n> --repo <owner>/<repo> --json headRefOid -q .headRefOid
```

To get the real line number a comment should sit on, fetch the file at that ref
and grep for the anchor text (diff hunk headers lie about final line numbers):

```
gh api "repos/<owner>/<repo>/contents/<path>?ref=<headRefOid>" -q .content \
  | base64 -d | grep -n "<anchor snippet>"
```

## 2. Build the payload
`event` must be `COMMENT` for a bot (never `APPROVE` / `REQUEST_CHANGES`).
Each comment: `path`, `line` (line in head file), `side: "RIGHT"`, `body`.
Prefix each body with a severity tag: `**[High]**`, `**[Medium]**`, `**[Low]**`.

```json
{
  "commit_id": "<headRefOid>",
  "event": "COMMENT",
  "body": "<summary: tally by severity + overall read>",
  "comments": [
    { "path": "src/gateways/ocr.gateway.ts", "line": 23, "side": "RIGHT",
      "body": "**[Medium]** No timeout bounds the OCR call; a dense image can pin CPU on the hot path. Wrap in a fail-closed timeout." }
  ]
}
```

Multi-line range: add `start_line` + `start_side` alongside `line`/`side`.
Two comments may target the same line.

## 3. POST it (Windows / Git-Bash gotcha)
`$TMPDIR` is often unset in the Bash tool here, and a bare relative path can land
in an unwritable dir. **Write the payload to the session scratchpad dir** (given
in the system prompt), then:

```
gh api repos/<owner>/<repo>/pulls/<n>/reviews \
  --method POST --input "<scratchpad>/review.json" -q '.html_url'
```

A successful call returns the review's `html_url`
(`…/pull/<n>#pullrequestreview-<id>`). Surface that in the Slack reply.

## 4. Notes
- One `reviews` POST publishes all inline comments atomically as a single review —
  preferred over N individual comment calls (avoids partial posts and rate limits).
- If a `line`/`path` doesn't exist in the diff, GitHub 422s the whole review;
  re-verify the anchor against the head file rather than retrying blindly.
- Keep the summary `body` short and factual; the value is in the inline comments.
