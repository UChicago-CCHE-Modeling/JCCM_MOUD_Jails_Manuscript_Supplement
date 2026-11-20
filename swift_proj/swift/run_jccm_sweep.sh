#! /usr/bin/env bash
set -eu

if [ "$#" -ne 2 ]; then
  script_name=$(basename $0)
  echo "Usage: ${script_name} EXPERIMENT_ID CONFIG_FILE(e.g. ${script_name} experiment_1 model.props)"
  exit 1
fi

# uncomment to turn on swift/t logging. Can also set TURBINE_LOG,
# TURBINE_DEBUG, and ADLB_DEBUG to 0 to turn off logging
# export TURBINE_LOG=1 TURBINE_DEBUG=1 ADLB_DEBUG=1
#export TURBINE_LOG=1 TURBINE_DEBUG=1 
export EMEWS_PROJECT_ROOT=$( cd $( dirname $0 )/.. ; /bin/pwd )

# source some utility functions used by EMEWS in this script
source "${EMEWS_PROJECT_ROOT}/etc/emews_utils.sh"

export EXPID=$1
export TURBINE_OUTPUT=$EMEWS_PROJECT_ROOT/experiments/$EXPID
check_directory_exists

# Fix for recent libpsm2 issue on bebop
export PSM2_KASSIST_MODE=none

# Edit the number of processes as required.
export PROCS=180

# TODO Edit QUEUE, WALLTIME, PPN, AND TURNBINE_JOBNAME
# as required. Note that QUEUE, WALLTIME, PPN, AND TURNBINE_JOBNAME will
# be ignored if the MACHINE variable (see below) is not set.
export QUEUE=bdwall
export PROJECT=emews
export WALLTIME=12:00:00
export PPN=18
export TURBINE_JOBNAME="${EXPID}_job"

# TODO Need to set the R_LIBS_USER env var on WSL since R user libs
#      may not be visibl to the root process running swift
#export R_LIBS_USER=/home/eric/R/x86_64-pc-linux-gnu-library/4.3

#export PYTHONPATH=$EMEWS_PROJECT_ROOT/python:$EMEWS_PROJECT_ROOT/ext/EQ-Py
# NOTE The python path should include the project root to reference hepcep_model
#export PYTHONPATH=${HOME}/jccm/JCCM
export PYTHONPATH=$EMEWS_PROJECT_ROOT/../

# TODO Edit command line arguments as appropriate
# for your run. Note that the default $* will pass all of this script's
# command line arguments to the swift script.
CMD_LINE_ARGS="$*"

CONFIG_FILE=$EMEWS_PROJECT_ROOT/../data/$2

# TODO Comment for local runs
# Bebop use srun
#export TURBINE_LAUNCHER=srun

# TODO Empty for local runs
# Bebop use pbs
MACHINE="pbs"
#MACHINE=""

if [ -n "$MACHINE" ]; then
  MACHINE="-m $MACHINE"
fi

# Need to create the output dir here to copy files below
mkdir -p $TURBINE_OUTPUT

# R file for model output response variables calculation
# ... copy specified file into the instance folder

R_RESPONSE_FILE=$EMEWS_PROJECT_ROOT/../analysis/jccm_analyze_run_response.R

RR_FILE=$TURBINE_OUTPUT/jccm_analyze_run_response.R
cp $R_RESPONSE_FILE $RR_FILE

CMD_LINE_ARGS+=" -rout_file=$RR_FILE"

#export TURBINE_LAUNCH_OPTIONS="--"

# Add any script variables that you want to log as
# part of the experiment meta data to the USER_VARS array,
# for example, USER_VARS=("VAR_1" "VAR_2")
USER_VARS=()
# log variables and script to to TURBINE_OUTPUT directory
log_script

# echo's anything following this standard out
set -x

swift-t -n $PROCS $MACHINE -p \
    $EMEWS_PROJECT_ROOT/swift/swift_run_sweep.swift \
    -f="$EMEWS_PROJECT_ROOT/data/moud/upf_moud_ntxxr_linkage_1.txt" \
    -config_file=$CONFIG_FILE \
    $CMD_LINE_ARGS
