#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo=$(CDPATH= cd -- "$root/../.." && pwd)
compiler=${TERRANE:-"$repo/target/debug/terrane"}
artifact=$("$compiler" build "$root/consumer/package.toml")
mkdir -p "$root/.trn/consumers"
cp "$artifact" "$root/.trn/consumers/template"
