#!/bin/sh
set -eu
exec python3 -c 'from waf_runtime.entrypoint import main; raise SystemExit(main())'
