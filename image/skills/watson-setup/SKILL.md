---
name: watson-setup
description: Set up or repair Watson's GitHub access — which repository to watch, which login's assigned issues to read, and the token to read them with. Trigger when the owner first messages this agent, when they ask Watson to watch a repository, or when the cycle reports that it has no configuration or no GitHub token.
allowed-tools: Bash(/opt/hermes/.venv/bin/watson:*), Bash(install:*), Bash(/usr/bin/gh:*)
---

# Watson setup

Three facts make Watson work, and the owner supplies all three. Ask for them one
at a time, in this order, and skip any you already have.

## 1. The repository

Ask which repository to watch, as `owner/repo`. Take one. Related repositories
can be added later; do not ask about them now.

## 2. The assignee

Ask which GitHub login's assigned issues are the owner's. Usually their own.
Watson reads only issues assigned to this login — that is the whole selection
rule, so getting it wrong means Watson sees nothing rather than too much.

## 3. The token

Ask for a **fine-grained personal access token** scoped to that repository, with
**Issues: read**, **Contents: read** and **Actions: read** — plus
**Pull requests: write** only if they want `repair` to open draft pull requests.
Point them at <https://github.com/settings/personal-access-tokens/new>.

Write it and nothing else, without it passing through your reply:

```bash
install -d -m 0700 /var/lib/hermes/watson
umask 077 && printf 'GH_TOKEN=%s\n' "$TOKEN" > /var/lib/hermes/watson/.env
```

Never echo the token, never put it in a GitHub comment, and never repeat it back
for confirmation. Confirm by what it can reach instead:

```bash
GH_TOKEN=$(. /var/lib/hermes/watson/.env; printf %s "$GH_TOKEN") \
  /usr/bin/gh api repos/OWNER/REPO --jq .full_name
```

The repository's name back means the token works. A failure means one of the
four permissions is missing — say which one the call needed and ask for a
replacement. Do not work around it.

## 4. Initialise

```bash
/opt/hermes/.venv/bin/watson --home /var/lib/hermes/watson init \
  --repo OWNER/REPO --assignee LOGIN --delivery text
```

`init` refuses to run twice. If it says this install is already configured and
the owner wants a different repository, tell them that is a new agent rather
than an edit, and stop.

## 5. Baseline

```bash
/opt/hermes/.venv/bin/watson --home /var/lib/hermes/watson sync
```

The first sync records a baseline and deliberately does **not** work through the
backlog. Say so plainly: issues assigned from now on are picked up on their own,
and anything already open has to be named.

```bash
/opt/hermes/.venv/bin/watson --home /var/lib/hermes/watson track 123
```

Then tell them the cycle runs by itself every ten minutes, and they will hear
from you when an issue actually moves — not on a schedule.
