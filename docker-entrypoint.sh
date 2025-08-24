#!/usr/bin/env sh
set -eu

cat >/app/config.yml <<EOF
trakt:
  client_id:      "131180931168c71c44673fb8b2896017bcf79b4791a504d2d91bec4120bff3d1"
  client_secret:  "1aed035ad7f62cfcd38c35f3ced19c8298e9d0f1dcb7dc553df32eb14808736b"
  recent_days:    ${TRAKT_RECENT_DAYS:-30}

radarr:
  enabled:        ${RADARR_ENABLED:-true}
  unmonitor:      ${RADARR_UNMONITOR:-true}
  tag:            ${RADARR_TAG:-watched}
  delete_file:    ${RADARR_DELETE_FILE:-false}
  address:        "${RADARR_ADDRESS:-}"
  apikey:         "${RADARR_APIKEY:-}"

sonarr:
  enabled:        ${SONARR_ENABLED:-true}
  unmonitor:      ${SONARR_UNMONITOR:-true}
  tag:            ${SONARR_TAG:-false}
  delete_file:    ${SONARR_DELETE_FILE:-false}
  address:        "${SONARR_ADDRESS:-}"
  apikey:         "${SONARR_APIKEY:-}"

medusa:
  enabled:        ${MEDUSA_ENABLED:-false}
  address:        "${MEDUSA_ADDRESS:-}"
  username:       "${MEDUSA_USERNAME:-}"
  password:       "${MEDUSA_PASSWORD:-}"
EOF

exec "$@"
