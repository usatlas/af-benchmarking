#! /bin/bash

curr_time=$(date -u "+%Y-%m-%dT%H:%M:%SZ")

container_el9 (){
  # Takes the following parameters:
  # - output_dir (1)
  # - job_dir (2)
  # - download_ID (3)
  export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
  export ALRB_localConfigDir="$HOME"/localConfig
# shellcheck disable=SC1091
  source "${ATLAS_LOCAL_ROOT_BASE}"/user/atlasLocalSetup.sh -c el9 -r "export RUCIO_ACCOUNT=jroblesg && \
    lsetup rucio &&\
    cat /home/$USER/pass.txt | voms-proxy-init -voms atlas && \
    mkdir -p ${1} &&\
    cd ${2} &&\
    rm -r ${3}/ &&\
    rucio download --rses AGLT2_LOCALGROUPDISK ${3}  2>&1 | tee rucio.log &&\
    hostname >> rucio.log &&\
    du ${3}/ >> rucio.log &&\
    mv rucio.log ${1}"
}


# Gets the current time

download_ID="mc23_13p6TeV.700866.Sh_2214_WWW_3l3v_EW6.deriv.DAOD_PHYSLITE.e8532_e8528_s4162_s4114_r14622_r14663_p6491"
# Conditional block determines the AF
# If the directory exists run the commands in the block
if [[ -d /sdf ]]; then
  user_name=$USER
  first_letter=${user_name:0:1}
  job_dir="$HOME/RucioJob"
  output_dir="/sdf/home/${first_letter}/${user_name}/benchmarks/${curr_time}/Rucio/"
  container_el9 "${output_dir}" "${job_dir}" "${download_ID}"
elif [[ -d /usatlas ]]
then
  job_dir="/atlasgpfs01/usatlas/scratch/$USER/RucioJob"
  output_dir="/atlasgpfs01/usatlas/data/$USER/benchmarks/${curr_time}/Rucio"
  container_el9 "${output_dir}" "${job_dir}" "${download_ID}"
elif [[ -d /data ]]
then
  job_dir="/data/$USER/RucioJob"
  output_dir="/data/$USER/benchmarks/${curr_time}/Rucio/"
  native_el9 "${output_dir}" "${job_dir}" "${download_ID}"
elif [[ -d /pscratch ]]
then
  user_name=$USER
  first_letter=${user_name:0:1}
  job_dir="/home/$USER/RucioJob/"
  output_dir="/home/$USER/benchmarks/${curr_time}/Rucio"
  container_el9 "${output_dir}" "${job_dir}" "${download_ID}"
fi
