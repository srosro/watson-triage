# Install Watson on Plow

Watson runs as a cloud agent on a Plow phone line. You text it; it reads the
GitHub issues assigned to you and reports what it actually found.

## What you need

A Plow account with a free line, and a GitHub fine-grained personal access token
for the repository you want watched. Nothing on your Mac, and no ChatGPT or
Codex account — the agent thinks through Plow's own inference.

## 1. Deploy

```sh
git clone https://github.com/plow-pbc/plow-agents.git
export PATH="$PWD/plow-agents/bin:$PATH"
plow-agents login          # text the activation phrase to the number it prints
plow-agents lines          # keep the ID of a line reported `free`
plow-agents image show watson-delltrak --jq .plow.image   # the current digest
plow-agents deploy "$(plow-agents image show watson-delltrak --jq .plow.image)" --line ln_xxx
plow-agents agents         # until the status is `running`
```

`image show` is a public read and needs no token. It prints the digest Plow
currently pins, so the deploy always names an immutable reference without
anybody pasting one by hand.

## 2. Text it

Text the number `plow-agents lines` showed. Watson asks for three things, one at
a time:

- **the repository** — `owner/repo`
- **the assignee** — the GitHub login whose assigned issues are yours. This is
  the whole selection rule, so a wrong login means Watson sees nothing rather
  than too much.
- **a token** — a fine-grained PAT scoped to that repository, with
  **Issues: read**, **Contents: read** and **Actions: read**. For `repair`, add
  **Contents: write** *and* **Pull requests: write** — it pushes the fix as a
  branch before opening the draft PR, so pull-request access alone cannot
  complete one. Create one at
  <https://github.com/settings/personal-access-tokens/new>.

Watson confirms the token by reading the repository's name back to you, never by
repeating the token.

## 3. What happens next

The first sync records a baseline and deliberately does **not** work through
your backlog. Issues assigned to you from then on are picked up on their own,
every ten minutes. To have Watson look at something already open, tell it the
number.

Watson never merges. `repair` opens a draft pull request, and only after a
regression test it wrote fails against the original source and passes against
the fix.

## Running it on your own machine instead

The same `cycle` runs locally — see the repository README. The local path still
needs the `plow-agents` CLI on your `PATH` (cloned as in step 1), `gh auth login`,
and a Plow credential for inference (`plow-agents mint`),
and it is the only path where browser validation and audio work, because both
need a desktop.
