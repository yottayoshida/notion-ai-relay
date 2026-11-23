#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
# Environment variables, not -W: -W does not reach the fixture and scorer processes the tests start.
# Keep "default" before the error entry: once PYTHONWARNINGS is set, unittest stops showing deprecation and
# resource warnings, and a later entry overrides an earlier one.
export PYTHONWARNDEFAULTENCODING=1 PYTHONWARNINGS=default,error::EncodingWarning
python3 -m unittest discover -s tests -v
