---
name: jwt-inspector
description: Decodes a JSON Web Token without verifying it, shows the header and claims with readable dates and flags risks such as alg none, a missing expiry, an expired token or a very long lifetime. Use when the user pastes a JWT and asks what is inside, why a token is rejected, or whether its settings look safe.
license: MIT
metadata:
  version: 1.0.0
  author: Lethe044
  tags: [jwt, auth, security, debugging]
---

# JWT inspector

Reads a token the way a debugger would. It never verifies the signature and never prints it.

## When to use

- The user pastes a token and asks what the claims say.
- An API answers 401 and the user suspects the token has expired or is not valid yet.
- A review needs a quick check of algorithm, expiry and lifetime.

## How to run

```bash
python scripts/inspect_jwt.py "eyJhbGciOi..."
echo "$TOKEN" | python scripts/inspect_jwt.py
python scripts/inspect_jwt.py "$TOKEN" --now 1700000000
```

A leading `Bearer ` is ignored. `--now` takes epoch seconds or an ISO time ending in `Z` and makes results repeatable.

## Output

JSON with `header`, `payload`, `alg`, `typ`, the times `issued_at`, `not_before` and `expires_at` (UTC),
`expired` (true, false or null when there is no expiry), `lifetime_seconds` and `warnings`.

Possible warnings: the algorithm is `none`, the signature is empty, there is no `exp` claim, the lifetime is longer
than 24 hours, the token is expired, the token is not valid yet.

## Safety

- Decoding is not verification. Anyone can create a token with any claims. Never use this output to decide whether
  to trust a token.
- Tokens are credentials. Tell the user to treat a pasted token as exposed if it is still valid, and to rotate it.
- Do not store tokens in files or logs while debugging.

## Errors

A value that is not a three part token with JSON header and payload exits with code 3.
