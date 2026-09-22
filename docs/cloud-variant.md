# The cloud variant

An image built `FROM` the pinned Plow base that runs Watson's own `cycle`
unattended on a tenant VM. Same collector, same SQLite state, same resumable
round — what changes is where the thinking happens and where the credentials
come from.

## What is different from the local install

**Inference is Plow's lane, not a Codex subscription.** `analysis.PlowInference`
calls `${PLOW_API_BASE}/v1/chat/completions` with the bearer `plow-init`
publishes as `HERMES_CUSTOM_PLOW_API_KEY`, on the model the base configures for
Hermes (`z-ai/glm-5.2`). There is no `codex login` and no ChatGPT account, and
this is the only backend — the local path uses it too, against a credential
minted by `plow-agents mint`.

**Browser validation and audio are dormant, not removed.** Both need a desktop:
Playwright drives a real Chromium, and the voice path reads a ChatGPT session
out of `~/.codex/auth.json`. The container configures no `browser_profiles`, so
`cycle` never reaches `run_browser`, and it never generates audio on its own —
`voice` and `deliver --audio` are explicit commands. Run Watson on your Mac when
you want the recorded evidence.

**The owner's GitHub token arrives over chat.** There is no `gh auth login` on a
tenant VM. The `watson-setup` skill writes a fine-grained PAT to
`/var/lib/hermes/watson/.env` mode 0600, and the cycle service reads it as root
before dropping to uid 10000 and hands it to that one invocation. It is never
published to the container environment, so nothing else in the image — the
gateway, the index reporter, the inference call — can see it.

## What this repository must not own

The base owns these, and a copy here is a second owner that goes stale silently:

| fact | owner |
|---|---|
| the `plow_chat` plugin SHA | `plow-hermes-agent`'s `ARG PLOW_CHAT_PLUGIN_SHA` |
| boot, identity, the dotenv, `SOUL.md` composition | `plow-init` |
| `PLOW_API_BASE`, `PLOW_AGENT_TOKEN`, `HERMES_CUSTOM_PLOW_API_KEY`, `AGENT_ID` | `plow-init`, published to the container environment |
| the inference provider, model and vision lane | the base's `config.yaml` seed |
| the Agent Index reporter and its pinned client | the base's `agent-index` service and `vendor/client.pin` |

This repository owns the persona, the `watson-setup` skill, the `watson-cycle`
service, and Watson itself. That is the whole list.

## The two credentials

| credential | where it comes from | what reads it |
|---|---|---|
| Plow bearer | `plow-init`, on first boot, from the line's credential | the gateway, the index reporter, and `PlowInference` |
| GitHub PAT | the owner, in chat, via `watson-setup` | `gh`, through `watson.github`, in the cycle service only |
