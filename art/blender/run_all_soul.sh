#!/bin/bash
# 重建三個魂系角色（含烘焙、匯出、預覽）
cd "$(dirname "$0")"
for m in hero sentinel executioner; do bash run_soul.sh $m "$@" > /tmp/soul_$m.log 2>&1; done
echo allfinished > /tmp/soul_all.log
