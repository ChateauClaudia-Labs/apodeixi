#!/usr/bin/env bash

abort_if_error() {
    if [[ $? != 0 ]]; then
        echo "[ERROR] Aborting"
        exit 1
    fi    
}

export SCRIPT_FOLDER="$( dirname $0 )"
source ${SCRIPT_FOLDER}/config.sh
abort_if_error

ORIGINAL_WORKING_DIR=$(pwd)

CCL_CHASSIS_GIT_REPO="https://github.com/ChateauClaudia-Labs/ccl-chassis.git"
APODEIXI_DEVOPS_GIT_REPO="https://github.com/ChateauClaudia-Labs/apodeixi-devops.git"

echo "[INFO] Setting up CI/CD tooling for Apodeixi"
echo 
echo "[INFO] CCL_CHASSIS_VERSION        = ${CCL_CHASSIS_VERSION}"
echo "[INFO] CCL_CHASSIS_HOME           = ${CCL_CHASSIS_HOME}"
echo "[INFO] APODEIXI_DEVOPS_VERSION    = ${APODEIXI_DEVOPS_VERSION}"
echo "[INFO] APODEIXI_DEVOPS_HOME       = ${APODEIXI_DEVOPS_HOME}"
echo

if [ ! -d ${CCL_CHASSIS_HOME} ]
    # In this case, we create the folder and install the tooling.
    # Otherwise we install nothing, since the tooling is already in place.
    then
        mkdir -p ${CCL_CHASSIS_HOME}
        abort_if_error

        WORKING_DIR=${CCL_CHASSIS_HOME}
        cd ${WORKING_DIR}

        echo "[INFO] git clone  ${CCL_CHASSIS_GIT_REPO} --branch ${CCL_CHASSIS_VERSION}"
        echo
        git clone  ${CCL_CHASSIS_GIT_REPO} --branch ${CCL_CHASSIS_VERSION}
        abort_if_error

        # Make sure the apdo CLI command is executable
        chmod 777 ${CCL_CHASSIS_HOME}/ccl-chassis/devops/bin/apdo
        abort_if_error
        # Make sure all shell scripts are executable
        find ${CCL_CHASSIS_HOME}/ccl-chassis/devops -type f -iname "*.sh" -exec chmod +x {} \;
        abort_if_error

fi

if [ ! -d ${APODEIXI_DEVOPS_HOME} ]
    # In this case, we create the folder and install the tooling.
    # Otherwise we install nothing, since the tooling is already in place.
    then
        mkdir -p ${APODEIXI_DEVOPS_HOME}
        abort_if_error

        WORKING_DIR=${APODEIXI_DEVOPS_HOME}
        cd ${WORKING_DIR}

        echo "[INFO] git clone  ${APODEIXI_DEVOPS_GIT_REPO} --branch ${APODEIXI_DEVOPS_VERSION}"
        echo
        git clone  ${APODEIXI_DEVOPS_GIT_REPO} --branch ${APODEIXI_DEVOPS_VERSION}
        abort_if_error
fi

echo "[INFO] Creating Apodeixi environments if needed"
UAT_ENV_DIR="${APODEIXI_DEVOPS_HOME}/UAT_ENV"
if [ ! -d ${UAT_ENV_DIR}/secrets ]
    then
        mkdir -p ${UAT_ENV_DIR}/secrets
        abort_if_error
fi
if [ ! -d ${UAT_ENV_DIR}/collaboration_area ]
    then
        mkdir -p ${UAT_ENV_DIR}/collaboration_area
        abort_if_error
fi
if [ ! -d ${UAT_ENV_DIR}/kb ]
    then
        mkdir -p ${UAT_ENV_DIR}/kb
        abort_if_error
fi

cd ${ORIGINAL_WORKING_DIR}

echo
echo "[INFO] To complete setup, type"
echo
echo "          cd ${SCRIPT_FOLDER}"
echo "          source env.sh"
echo
echo "[INFO] After that, type 'apdo --help' to access tooling CLI"