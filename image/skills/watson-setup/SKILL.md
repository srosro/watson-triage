---
name: watson-setup
description: Set up Watson — which repository to watch and which login's assigned issues to read. Trigger when the owner first messages this agent, when they ask Watson to watch a repository, or when the cycle reports that it has no configuration.
allowed-tools: Bash(/opt/hermes/.venv/bin/watson:*), Bash(/usr/local/bin/gh:*)
---

# Watson setup

Two facts make Watson work, and the owner supplies both. Ask one at a time.

**Never ask the owner for a GitHub token, and refuse if they offer one.** A
token they text is in this conversation, which means it is in the model's
context and therefore at the inference provider — a repository credential
disclosed to a third party, and nothing can hold it at arm's length once it has
been said out loud. The token is deploy-time input, set where the container is
started. If it is missing, say so and point at `docs/INSTALL.md`; do not offer
to accept one here as a workaround.

## 1. The repository

Ask which repository to watch, as `owner/repo`. Take one. Related repositories
can be added later; do not ask about them now.

## 2. The assignee

Ask which GitHub login's assigned issues are the owner's. Usually their own.
Watson reads only issues assigned to this login — that is the whole selection
rule, so a wrong login means Watson sees nothing rather than too much.

## 3. Check the token that is already there

```bash
/usr/local/bin/gh api repos/OWNER/REPO --jq .full_name
```

The repository's name back means the deploy-time token reaches it. An auth
failure means the container was started without a usable `GH_TOKEN` — tell the
owner that, and that it is fixed where the agent is deployed, not here.

A token that reads the repository but is short a permission surfaces on the
first cycle, in that cycle's own error — report that error verbatim and name
the permission it asks for.

## 4. Initialise

```bash
/opt/hermes/.venv/bin/watson --home /var/lib/hermes/watson init \
  --repo OWNER/REPO --assignee LOGIN --delivery text --notify-owner
```

`--notify-owner` is what makes Watson message the owner when an issue moves.
Without it `notify()` returns immediately and every update is dropped in
silence, so leave it on unless the owner asks for a quiet agent.

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
