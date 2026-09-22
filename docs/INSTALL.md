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

## 2. Give it a GitHub token — at deploy time, not in chat

**Watson will not accept a token you text it, and will refuse if you offer.** A
token in the conversation is in the model's context and therefore at the
inference provider; that is a repository credential handed to a third party, and
nothing downstream can undo it.

Create a **fine-grained PAT** scoped to the repository, with **Issues: read**,
**Contents: read** and **Actions: read**. For `repair`, add **Contents: write**
*and* **Pull requests: write** — it pushes the fix as a branch before opening the
draft PR, so pull-request access alone cannot complete one. Create one at
<https://github.com/settings/personal-access-tokens/new>.

Running locally with compose, put the **raw token** in `./watson-github` — no
`GH_TOKEN=` prefix, nothing else in the file — and lock it down:

```sh
printf %s 'github_pat_…' > watson-github && chmod 600 watson-github
```

It is bind-mounted read-only into the container, which is why it is a bare
value rather than an env file: it never enters the container environment, where
the agent's own shell could read it.

**One caveat, measured rather than assumed.** A bind mount's permissions are
enforced by the host's filesystem. Linux enforces them, so `root:root 0600`
means the agent cannot open the file. **Docker Desktop on macOS does not** — the
file reports `0600` to `stat` and the agent reads it anyway. The cycle warns
loudly when it detects this. It is fine for local development, where the
exposure is to your own agent on your own machine; do not treat a Mac compose
run as isolated.

On the hosted path, `plow-agents deploy` injects only the `PLOW_*` variables, so
there is no hook for this yet and the agent stands down with "no GH_TOKEN"
until [issue #2](https://github.com/srosro/watson-triage/issues/2) lands device
authorization. **Until then, the hosted path is deploy-only — run Watson under
compose if you want it working today.**

## 3. Text it

Text the number `plow-agents lines` showed. Watson asks for two things:

- **the repository** — `owner/repo`
- **the assignee** — the GitHub login whose assigned issues are yours. This is
  the whole selection rule, so a wrong login means Watson sees nothing rather
  than too much.

It does not check the token — it has no access to one, deliberately. The first
supervised cycle is what proves it, and an auth failure surfaces there.

## 4. What happens next

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
