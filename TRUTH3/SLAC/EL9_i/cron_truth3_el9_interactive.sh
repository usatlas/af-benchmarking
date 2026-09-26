#!/bin/bash

ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=20 iana "
cd /sdf/home/q/qlei/TRUTH3_int/el || exit

rm -r ./*

~/AF-Benchmarking/TRUTH3/SLAC/EL9_i/run_truth3_el9_interactive.sh"
