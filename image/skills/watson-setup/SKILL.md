---
name: watson-setup
description: Set up or repair Watson's GitHub access — which repository to watch, which login's assigned issues to read, and the token to read them with. Trigger when the owner first messages this agent, when they ask Watson to watch a repository, or when the cycle reports that it has no configuration or no GitHub token.
allowed-tools: Bash(/opt/hermes/.venv/bin/watson:*), Bash(/opt/plow/watson-store-token:*), Bash(/usr/local/bin/gh:*)
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
rule, so a wrong login means Watson sees nothing rather than too much.

## 3. Initialise, before asking for anything secret

```bash
/opt/hermes/.venv/bin/watson --home /var/lib/hermes/watson init \
  --repo OWNER/REPO --assignee LOGIN --delivery text
```

`init` refuses to run twice. If it says this install is already configured and
the owner wants a different repository, tell them that is a new agent rather
than an edit, and **stop here** — do not go on to ask for a token. Asking first
and initialising second would replace a working install's credential with one
scoped to a repository this agent will never watch.

## 4. The token

Ask for a **fine-grained personal access token** scoped to that repository:

| permission | why |
|---|---|
| Issues: read | the issues themselves and their conversations |
| Contents: read | the source the investigation cites |
| Actions: read | run results and failed steps |
| Contents: **write** | only for `repair` — it pushes the fix as a branch |
| Pull requests: **write** | only for `repair` — the draft PR on that branch |

Both write permissions are needed together for repairs: `repair` creates a tree,
a commit and a ref before it opens the pull request, so pull-request access
alone cannot complete one. Point the owner at
<https://github.com/settings/personal-access-tokens/new>.

Store it by piping it to the helper, which reads stdin, checks the shape, and
writes `0600`:

```bash
printf %s 'THE_TOKEN' | /opt/plow/watson-store-token
```

It prints `stored`, never the token. Do not echo the token back to the owner,
do not put it in a GitHub comment, and do not repeat it for confirmation.

Confirm by what it can reach:

```bash
/usr/local/bin/gh api repos/OWNER/REPO --jq .full_name
```

The repository's name back means the token reaches the repository. If it fails,
say so and ask for a replacement rather than working around it. A token that
reads the repository but is short a permission surfaces on the first cycle, in
that cycle's own error — report that error to the owner verbatim and name the
permission it asks for.

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
