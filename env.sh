# source this: . env.sh
module load gcc arrow cuda python/3.13   # arrow provides pyarrow (needed for Parquet)
source /project/rpp-nahee/hamza95/python313/bin/activate
export AGENT_ROOT=/project/rpp-nahee/hamza95/agent_challenge
export PYTHONPATH=$AGENT_ROOT/src:$PYTHONPATH
# Needs ANTHROPIC_API_KEY set in your shell (never commit it)
