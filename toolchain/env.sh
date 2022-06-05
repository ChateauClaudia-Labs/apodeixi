source ./config.sh

echo "[INFO] Setting environment variables"

export PATH="${CCL_CHASSIS_HOME}/ccl-chassis/devops/bin":$PATH
export _CFG__PIPELINE_ALBUM="${APODEIXI_DEVOPS_HOME}/apodeixi-devops/pipeline_album"
export _CFG__PIPELINE_HISTORY="../apdo_builds"

echo "[INFO] PATH                       = ${PATH}"
echo "[INFO] _CFG__PIPELINE_ALBUM       = ${_CFG__PIPELINE_ALBUM}"
echo "[INFO] _CFG__PIPELINE_HISTORY     = ${_CFG__PIPELINE_HISTORY}"