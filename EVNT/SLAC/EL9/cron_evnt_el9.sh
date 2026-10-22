#!/bin/bash

# Submission, waiting for completion, parsing, and uploading all happen in
# submit_and_upload.sh on iana (the Slurm submit host) -- see that file for
# why this is a single script rather than a multi-line ssh block.
# Keepalives are needed because this ssh session blocks for the job's full
# walltime.
ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=20 iana \
  '$HOME/AF-Benchmarking/EVNT/SLAC/EL9/submit_and_upload.sh'
