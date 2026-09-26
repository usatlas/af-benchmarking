#!/bin/bash

# Submission, waiting for completion, parsing, and uploading all happen in
# submit_and_upload.sh on iana (the Slurm submit host) -- see that file for
# why this is one script rather than the multi-line ssh block this used to
# be. Keepalives are needed because this ssh session now blocks for the
# job's full walltime (up to 2h for this job).
ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=20 iana \
  '$HOME/AF-Benchmarking/EVNT/SLAC/CentOS7/submit_and_upload.sh'
