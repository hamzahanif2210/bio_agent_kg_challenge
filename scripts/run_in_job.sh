#!/bin/bash
# Run a command inside an existing interactive job: scripts/run_in_job.sh JOBID cmd...
J=$1; shift
srun --jobid=$J --overlap bash -c "cd /project/rpp-nahee/hamza95/agent_challenge && source env.sh >/dev/null 2>&1 && $*"
