#!/usr/bin/env bash
set -euo pipefail

# Cloud-friendly wrapper that runs EC Train for 10 random unique contracts.
# Uses the built-in sample BidTabs file unless EC_TRAIN_BIDTABS_PATH is provided.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="${EC_TRAIN_OUTPUT_DIR:-${ROOT_DIR}/ec_train_output/cloud_run}"

export EC_TRAIN_DOWNLOAD_DIR="${EC_TRAIN_DOWNLOAD_DIR:-${OUTPUT_DIR}/downloads}"

mkdir -p "${OUTPUT_DIR}"

ec-train run \
  --count 10 \
  --headless \
  --force-new-session \
  --output-dir "${OUTPUT_DIR}" \
  "$@"
