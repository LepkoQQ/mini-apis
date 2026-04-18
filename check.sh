#!/usr/bin/env bash

require_tool() {
  if ! command -v "$1" &> /dev/null
  then
    echo "$1 not found in path"
    exit 1
  fi
}

require_tool black
require_tool isort
require_tool mypy

# change directory to the app directory
cd ./mini-apis

exit_code=0

if [[ "$1" == "--fix" ]]; then
  # run formatters if "--fix" argument is passed
  echo "Running formatters..."
  black . --quiet || exit_code=1
  isort . --quiet --profile black || exit_code=1
else
  # run black and isort in check mode otherwise
  echo "Checking formatting... (run with --fix to format)"
  black . --quiet --check --diff || exit_code=1
  isort . --quiet --check --diff --profile black || exit_code=1
fi

# run mypy
echo "Checking types..."
mypy . --no-error-summary || exit_code=1

exit $exit_code
