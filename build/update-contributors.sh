#!/usr/bin/env bash

contributors=CONTRIBUTORS
[[ -f "$contributors".tmp ]] && rm -f "$contributors".tmp
git shortlog -s | grep -vE "dependabot|synk-bot" | cut -f2- > "$contributors".tmp
sort -u CONTRIBUTORS.tmp > CONTRIBUTORS
[[ -f "$contributors".tmp ]] && rm -f "$contributors".tmp
