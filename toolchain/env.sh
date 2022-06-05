source ./config.sh

echo "[INFO] Setting environment variables"

export PATH="${CCL_CHASSIS_HOME}/ccl-chassis/devops/bin":$PATH
export _CFG__PIPELINE_ALBUM="${APODEIXI_DEVOPS_HOME}/apodeixi-devops/pipeline_album"

echo "[INFO] PATH                   = ${PATH}"
echo "[INFO] _CFG__PIPELINE_ALBUM   = ${_CFG__PIPELINE_ALBUM}"