#!/bin/bash

ADB_PATH="/Users/lymanyang/Library/Android/sdk/platform-tools/adb"
DEVICES_LIST=$(${ADB_PATH} devices | grep -v "devices attached")

DEVICE_NAME=""

for DEVICE in ${DEVICES_LIST}; do
	if [[ (! $DEVICE =~ emulator) && (! $DEVICE =~ device) ]]; then
		DEVICE_NAME=$DEVICE
	fi
done

if [[ -z $DEVICE_NAME ]]; then
	exec ${ADB_PATH} devices
	exit -1
fi

NEW_ADB=${ADB_PATH}
PADDING=" "
NEW_ADB=${NEW_ADB}" -d"

# 将输入的参数进行组装
param_count=0
total_count=$#

while [ $param_count -lt $total_count ]; do
	if [[ $param_count == 0 && $1 == "install" ]]; then
		NEW_ADB=$NEW_ADB" -s ${DEVICE_NAME}"
	fi
	NEW_ADB=$NEW_ADB$PADDING$1	
	# shift param to $1
	shift
	param_count=$((param_count + 1))
done

echo "Execute adb: ${NEW_ADB}"
exec $NEW_ADB
