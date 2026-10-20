#!/usr/bin/env bash
# Download the newest web release of every app in apps.json into <out>/<id>/ and verify it.
# Every good download is also saved as a backup release in this repository. If the upstream
# release can't be fetched or fails its checksum, the backup is used instead.
#
# usage: fetch_apps.sh apps.json out_dir        (needs gh, jq; GH_TOKEN and GITHUB_REPOSITORY set)
set -uo pipefail

CONFIG=${1:?usage: fetch_apps.sh apps.json out_dir}
OUT=${2:?usage: fetch_apps.sh apps.json out_dir}
MY_REPO=${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is not set}

fetch_upstream() { # repo pattern dir
  local repo=$1 pattern=$2 dir=$3 tag
  tag=$(gh release view --repo "$repo" --json tagName -q .tagName) || return 1
  [ -n "$tag" ] || return 1
  gh release download "$tag" --repo "$repo" --pattern "$pattern" --pattern 'SHA256SUMS.txt' --dir "$dir" || return 1
  [ "$(find "$dir" -maxdepth 1 -name '*.zip' | wc -l)" -eq 1 ] || return 1
  (cd "$dir" && sha256sum -c --ignore-missing SHA256SUMS.txt) || return 1
  printf '%s' "$tag" > "$dir/TAG"
}

backup_zip() { # id dir tag
  local id=$1 dir=$2 tag=$3 rel="backup-$1" zip name have old
  zip=$(find "$dir" -maxdepth 1 -name '*.zip')
  name=$(basename "$zip")
  if ! gh release view "$rel" --repo "$MY_REPO" > /dev/null 2>&1; then
    gh release create "$rel" --repo "$MY_REPO" --title "$tag" \
      --notes "Backup copy of the upstream web build of $id. Used automatically if the upstream release is gone." || return 1
  fi
  have=$(gh release view "$rel" --repo "$MY_REPO" --json assets -q '.assets[].name') || return 1
  if ! grep -qxF "$name" <<< "$have"; then
    gh release upload "$rel" "$zip" --repo "$MY_REPO" --clobber || return 1
    gh release edit "$rel" --repo "$MY_REPO" --title "$tag" || return 1
    for old in $have; do
      gh release delete-asset "$rel" "$old" --repo "$MY_REPO" --yes || true
    done
  fi
}

fetch_backup() { # id dir
  local id=$1 dir=$2 rel="backup-$1" tag
  gh release download "$rel" --repo "$MY_REPO" --pattern '*.zip' --dir "$dir" || return 1
  tag=$(gh release view "$rel" --repo "$MY_REPO" --json name -q .name) || return 1
  [ -n "$tag" ] || return 1
  printf '%s' "$tag" > "$dir/TAG"
}

failed=0
mkdir -p "$OUT"
for id in $(jq -r '.[].id' "$CONFIG"); do
  repo=$(jq -r --arg id "$id" '.[] | select(.id == $id) | .repo' "$CONFIG")
  pattern=$(jq -r --arg id "$id" '.[] | select(.id == $id) | .asset' "$CONFIG")
  dir="$OUT/$id"
  rm -rf "$dir"; mkdir -p "$dir"

  if fetch_upstream "$repo" "$pattern" "$dir"; then
    echo "$id: upstream $(cat "$dir/TAG")"
    backup_zip "$id" "$dir" "$(cat "$dir/TAG")" || echo "::warning::$id: could not save the backup copy"
  else
    echo "::warning::$id: upstream download failed, trying the backup copy"
    rm -rf "$dir"; mkdir -p "$dir"
    if fetch_backup "$id" "$dir"; then
      echo "$id: using backup $(cat "$dir/TAG")"
    else
      echo "::error::$id: no upstream release and no backup copy"
      failed=1
    fi
  fi
done
exit $failed
