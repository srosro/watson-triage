# The Plow cloud image: Watson, built for Plow to run as a cloud agent.
#
# The tag is an immutable `base-<sha>` naming one commit of the base's source
# repo, plow-pbc/plow-hermes-agent. It is never moved: every tenant VM inherits
# this exact filesystem while holding that owner's Plow credential, so a moving
# tag would substitute code underneath them. This is the newest tag the registry
# has published.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-67021a7029e33e80bcb27899be6515a5a0e9b37b

# Identity: only what is specific to this agent. plow-init writes the home's
# SOUL.md on every boot as the base persona followed by this file; nothing is
# COPYed to /var/lib/hermes/SOUL.md, which is overwritten at boot.
COPY image/persona.md /opt/hermes/plow-seed/persona.md
# The mode in its own step: `COPY --chmod=` is BuildKit-only, and a stock Docker
# still selects the legacy builder, where it fails the build outright.
RUN chmod 0644 /opt/hermes/plow-seed/persona.md

# Both copies, as the base image does. /var/lib/hermes/skills is what a home
# that starts empty is seeded from and what the gateway reads; /opt/hermes/skills
# is outside every home, so a bind-mounted home still receives it and an image
# update still reaches a skill the agent has not customised.
COPY --chown=10000:10000 image/skills/ /var/lib/hermes/skills/
COPY --chown=10000:10000 image/skills/ /opt/hermes/skills/

# `gh` is how watson.github reads the API and how `repair` opens its draft pull
# request. Pinned by version AND checksum, for the same reason the base pins the
# index client that way: this binary runs inside an agent holding a live
# credential, and a sha in a URL is only as good as the host serving it.
# linux/amd64 because that is what `plow-agents image build` produces.
ARG GH_VERSION=2.101.0
ARG GH_SHA256=9bca2d1c16825f109907a23307628a2f0698fbf99662b73a5cf0b020293072b8
RUN set -eu; \
    tarball="gh_${GH_VERSION}_linux_amd64.tar.gz"; \
    curl -fsS --max-time 120 -L -o "/tmp/$tarball" \
      "https://github.com/cli/cli/releases/download/v${GH_VERSION}/${tarball}"; \
    echo "${GH_SHA256}  /tmp/$tarball" | sha256sum -c -; \
    tar -xzf "/tmp/$tarball" -C /tmp; \
    install -m 0755 "/tmp/gh_${GH_VERSION}_linux_amd64/bin/gh" /usr/local/bin/gh; \
    rm -rf "/tmp/$tarball" "/tmp/gh_${GH_VERSION}_linux_amd64"; \
    gh --version

# Watson itself, into the runtime's own venv -- the one the cycle service calls
# by absolute path. `--no-deps` the way the base installs its one extra package:
# this project declares no runtime dependencies, and resolving any would let the
# install move a version the pinned base chose. The import check is the build's,
# so a boot that could not start Watson fails here instead.
COPY pyproject.toml /opt/watson/pyproject.toml
COPY watson/ /opt/watson/watson/
RUN set -eu; \
    uv pip install --python /opt/hermes/.venv/bin/python --no-deps /opt/watson; \
    /opt/hermes/.venv/bin/watson --help >/dev/null

# The boot layer. COPY merges into the base's tree, so its own `user` bundle
# entries survive alongside this one:
#
#   watson-cycle  longrun, one `watson cycle` every ten minutes, depends on plow-init
#
# No agent-index service here: the base already ships that reporter and the
# client it runs. A variant supplies AGENT_ID and nothing else.
COPY image/s6-overlay/ /etc/s6-overlay/
RUN chmod 0755 /etc/s6-overlay/s6-rc.d/watson-cycle/run

COPY LICENSE /usr/share/doc/watson/
