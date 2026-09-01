# The agent, packaged to run on a host that is not a Mac and has no agent-mgr.
#
# agent-mgr builds the agent's home on the operator's machine: it installs the
# Plow Chat plugin, the fleet skills, config.yaml, and runs this repo's
# deploy-hook. None of that exists on Railway, where the volume starts empty --
# so the home is baked into the image as a seed and unpacked by an s6 init
# script before the gateway starts.
#
# Pinned by digest, the same one runtime/stack.json pins, so this image and the
# local container run identical Hermes.
FROM nousresearch/hermes-agent@sha256:c84f3494f86ae32d6a82a3b7d56111d712f3d82f75f9744e8ae07668889714c2

# The seeded home. Built by deploy/railway/build-seed.sh from a deployed local
# home, because the plugin and fleet skills are fetched by agent-mgr through
# `gh` and cannot be reconstructed here.
COPY seed /opt/seed

# Runs before the gateway: s6 executes /etc/cont-init.d in name order, and the
# image's own setup is 01-hermes-setup, so 00- lands first.
COPY deploy/railway/00-agent-seed /etc/cont-init.d/00-agent-seed
RUN chmod +x /etc/cont-init.d/00-agent-seed

# Baked in rather than set as the platform's start command. The image's
# entrypoint is s6 (`/init`) wrapping main-wrapper.sh, whose routing is:
# no args -> `hermes` (the interactive CLI, not the gateway); anything else ->
# `hermes <args>`. So the gateway needs these two words to arrive as the
# container's CMD. A platform "start command" is executed as a program instead,
# and there is no `gateway` binary to find -- which is exactly how the first
# Railway deploy failed (CREATE_CONTAINER: executable `gateway` not found).
CMD ["gateway", "run"]
