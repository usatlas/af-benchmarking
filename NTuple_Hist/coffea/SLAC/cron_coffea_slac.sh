#!/bin/bash

# Submission, waiting for completion, parsing, and uploading all happen in
# submit_and_upload.sh on iana (the Slurm submit host) -- see that file for
# why this is one script rather than the multi-line ssh block this used to
# be. Keepalives are needed because this ssh session now blocks for the
# job's full walltime.
ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=20 iana \
  /sdf/home/q/qlei/AF-Benchmarking/NTuple_Hist/coffea/SLAC/submit_and_upload.sh
