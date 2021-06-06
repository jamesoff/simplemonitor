#!/usr/bin/env bash

contributors=CONTRIBUTORS
[[ -f "$contributors".tmp ]] && rm -f "$contributors".tmp
git shortlog -s | awk '!/dependabot/ {print $2}' > "$contributors".tmp
sort -u CONTRIBUTORS.tmp > CONTRIBUTORS
[[ -f "$contributors".tmp ]] && rm -f "$contributors".tmp
