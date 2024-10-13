#!/bin/bash

# start_daemon.shと同じディレクトリに移動
cd $(dirname "$(realpath "${BASH_SOURCE[0]}")")

source ./bin/activate
python scripts/main.py
deactivate

