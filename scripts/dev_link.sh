#!/usr/bin/env bash
set -euo pipefail

profile="${1:-copilot-dev}"
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
source_dir="$repo_root/geoutility_copilot"

case "$(uname -s)" in
  Darwin) plugins_dir="$HOME/Library/Application Support/QGIS/QGIS3/profiles/$profile/python/plugins" ;;
  *) plugins_dir="$HOME/.local/share/QGIS/QGIS3/profiles/$profile/python/plugins" ;;
esac

if [[ ! -d "$source_dir" ]]; then
  printf 'Plugin package not found: %s\n' "$source_dir" >&2
  exit 1
fi

mkdir -p "$plugins_dir"
target="$plugins_dir/geoutility_copilot"

if [[ -e "$target" && ! -L "$target" ]]; then
  printf 'Target exists and is not a symlink: %s\n' "$target" >&2
  exit 1
fi

ln -sfn "$source_dir" "$target"
printf 'Linked %s -> %s\n' "$target" "$source_dir"
