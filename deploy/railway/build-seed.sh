#!/bin/sh
# Refresh seed/ from a deployed local home.
#
# Run after `agent-mgr deploy <name>` whenever the plugin or the fleet skills
# move, and after editing anything this repo authors. The result is committed:
# Railway builds from the repo and has no agent-mgr, no `gh`, and no Mac.
#
# What is deliberately NOT copied: .env (credentials, set on the platform) and
# everything the agent accumulates -- sessions, cron, state.db, the record.
set -eu
cd "$(dirname "$0")/../.."

home="${1:-$HOME/.hermes-nina}"
[ -d "$home" ] || { echo "no home at $home -- pass one as \$1" >&2; exit 1; }

rm -rf seed
mkdir -p seed

# Only what the image does NOT ship. The image bundles ~70 skills into the home
# on first boot; seeding those would be 7MB of files that regenerate anyway, and
# would pin them to whatever version this seed was cut from. These three are the
# ones agent-mgr fetches from outside the image (two fleet skills through `gh`,
# and this repo's own).
for path in SOUL.md config.yaml plugins \
            skills/growth/plow-invite \
            skills/productivity/google-workspace \
            skills/health/prenatal; do
  [ -e "$home/$path" ] || { echo "missing $home/$path -- deploy first" >&2; exit 1; }
  mkdir -p "seed/$(dirname "$path")"
  cp -R "$home/$path" "seed/$path"
done

# The record is state, not seed: only the empty shape travels.
mkdir -p seed/nina/exams

find seed -name '.DS_Store' -delete
echo "seed refreshed from $home:"
find seed -maxdepth 2 -mindepth 1 | sort | sed 's/^/  /'
