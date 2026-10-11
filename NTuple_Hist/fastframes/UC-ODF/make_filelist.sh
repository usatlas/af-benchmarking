#!/bin/bash

# Prints the FastFrames input file list for the mc20e Wmunugamma ntuples held
# in a directory, one line per .root file. The columns (DSID, campaign,
# simulation type) are those of the list kept for UC, which names the same
# ntuples by their UC paths.
#
# Usage: make_filelist.sh NTUPLE_DIR > mc20e_filelist.txt

ntuple_dir="${1:?Usage: make_filelist.sh NTUPLE_DIR}"

# An unmatched glob must expand to nothing, not to the literal pattern
shopt -s nullglob
files=("${ntuple_dir%/}"/*.root)

if [[ ${#files[@]} -eq 0 ]]; then
  echo "make_filelist.sh: no .root files in ${ntuple_dir}" >&2
  exit 1
fi

for file in "${files[@]}"; do
  printf '700402  mc20e   fullsim %s\n' "${file}"
done
