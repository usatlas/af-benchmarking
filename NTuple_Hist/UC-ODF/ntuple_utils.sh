#!/bin/bash

# Shared checks for the UC-ODF ntuple jobs (EventLoop, Coffea, FastFrames).

# Exits unless NTUPLE_DIR is an absolute path to a directory holding .root
# files. Without this, an empty or wrong directory runs "successfully" on zero
# events and produces a plausible-looking benchmark. The path must be absolute
# because it is mounted into the container and exported again inside it.
require_ntuple_dir() {
  : "${NTUPLE_DIR:?Set NTUPLE_DIR to the directory holding the mc20e ntuples}"

  if [[ "${NTUPLE_DIR}" != /* ]]; then
    echo "NTUPLE_DIR must be an absolute path, got: ${NTUPLE_DIR}" >&2
    exit 1
  fi

  if ! compgen -G "${NTUPLE_DIR%/}/*.root" > /dev/null; then
    echo "No .root files in NTUPLE_DIR: ${NTUPLE_DIR}" >&2
    exit 1
  fi
}
