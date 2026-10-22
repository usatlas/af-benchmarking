#!/bin/bash

# Prepares the sources that build_fastframes.sh compiles: a clone of FastFrames
# at the commit the UC-ODF pilot built and benchmarked, and the TutorialClass
# custom class from this repo.
#
# Usage: FF_DIR=/path/to/FastFramesTutorial ./fetch_fastframes_sources.sh
# FASTFRAMES_URL and FASTFRAMES_COMMIT override the defaults, for testing.

: "${FF_DIR:?Set FF_DIR to the directory the FastFramesTutorial tree is built in}"

fastframes_url="${FASTFRAMES_URL:-https://gitlab.cern.ch/atlas-amglab/fastframes.git}"
fastframes_commit="${FASTFRAMES_COMMIT:-3ba8ff37296364d7f70702e587d0475f41f05db1}"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

mkdir -p "${FF_DIR}"

if [[ ! -d "${FF_DIR}/FastFrames/.git" ]]; then
  # The Git LFS test inputs (about 100 MB) are not needed to build
  export GIT_LFS_SKIP_SMUDGE=1
  git clone --quiet "${fastframes_url}" "${FF_DIR}/FastFrames" || exit 1
  git -C "${FF_DIR}/FastFrames" checkout --quiet "${fastframes_commit}" || exit 1
fi

# An existing clone is never moved: building a different FastFrames than the
# one benchmarked elsewhere would silently change what is measured
current=$(git -C "${FF_DIR}/FastFrames" rev-parse HEAD)
if [[ "${current}" != "${fastframes_commit}" ]]; then
  echo "FastFrames in ${FF_DIR}/FastFrames is at ${current}, expected ${fastframes_commit}" >&2
  exit 1
fi

# Edits in the repo reach the build, but only files whose content changed are
# copied. A plain copy gives every file a new timestamp, which would recompile
# and relink the library on every run, rewriting a file that another run on
# this shared volume may be loading.
mkdir -p "${FF_DIR}/TutorialClass"
(cd "${script_dir}/TutorialClass" && find . -type f -print0) |
  while IFS= read -r -d '' file; do
    if ! cmp -s "${script_dir}/TutorialClass/${file}" "${FF_DIR}/TutorialClass/${file}"; then
      mkdir -p "$(dirname -- "${FF_DIR}/TutorialClass/${file}")"
      cp "${script_dir}/TutorialClass/${file}" "${FF_DIR}/TutorialClass/${file}"
    fi
  done
