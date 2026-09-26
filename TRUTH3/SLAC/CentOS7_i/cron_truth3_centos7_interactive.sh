#!/bin/bash

ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=20 iana "
cd /sdf/home/q/qlei/TRUTH3_int/centos || exit

rm -r ./*

~/AF-Benchmarking/TRUTH3/SLAC/CentOS7_i/run_truth3_centos7_interactive.sh"
