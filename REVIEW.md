# Review instructions — watson-triage

Reviewer-facing policy for this repo. Read it before any other input. The
universal review-loop rules are org policy, supplied by the reviewer, and are
deliberately not copied here.

## What this repo is

Watson reads GitHub issues assigned to one login, investigates them against the
repository's own source and CI, and reports to its owner. This fork adds one
thing upstream does not have: a **Plow Hermes cloud variant** — an image built
`FROM` the pinned Plow base that runs the same `watson cycle` unattended, with
Plow as the inference lane instead of a local Codex subscription.

Read first: `README.md`, `docs/architecture.md`, `docs/hermes-plow.md`.
(`docs/cloud-variant.md` joins that list when the variant PR lands; until
then it is not on this branch, and a policy that sends a reviewer to a
missing file supplies no context at all.)

**Operating point:** one operator, zero tenants, pre-PMF, fork of a hackathon
prototype. The bottleneck is getting one image to boot and report, not scale.

## Posture

- **Over-engineering is the primary catch.** Flag premature abstraction,
  defensive guards for cases that cannot happen at one tenant, fallback chains
  and wrappers for one call site. Lead with the deletion / inline-it remedy.
  Net-negative LOC per round is the target; a round that only adds is a smell.
- **One owner per fact.** The base image owns the plugin pin, the boot, the env
  names and the inference config; this repo owns the persona, the skills and the
  cycle service. A finding that this repo re-pins, re-derives or second-guesses a
  base-owned fact is `[blocking]` — that is the defect class this variant is most
  likely to introduce. Test: could `plow-pbc/plow-hermes-agent` change this fact
  and leave a copy here stale?
- **Credentials are named, never echoed.** The owner's GitHub PAT and the Plow
  bearer reach the cycle service through the container environment. Flag any path
  that writes either into a log line, a GitHub comment, a model prompt, or an
  image layer. `analysis.Plow` must not forward `GH_TOKEN` to inference, the way
  `Codex` did not.
- **Model output is untrusted evidence.** Every value the model returns crosses a
  schema check before it reaches GitHub, the owner, or the browser plan. A finding
  that a new path skips `validate_result` (or its equivalent) is `[blocking]`.
  Prompt text asking the model to be careful is not a control.
- **Security findings must name a practical, currently-reachable loss.** State the
  concrete loss in access or data if it fires today. No nameable loss beyond a
  bounded one → at most `[low]`, question-voiced.
- **Watson never merges.** On **GitHub**, anything that can merge a PR,
  force-push, or write outside a draft PR and an issue comment is `[blocking]`
  regardless of how it is gated. This is about GitHub only: delivering an update
  to the owner over Plow/iMessage is the product working, not a write to flag —
  `notify()` is gated on the owner's own `notify_owner` setting, and reading a
  general "no writes" rule onto it would have a reviewer reject the feature the
  agent exists to provide.

## Update cadence

Edit only when the review *posture* shifts. Product and architecture facts belong
in `README.md` and `docs/`, not here.
