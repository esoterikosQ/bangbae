#!/bin/bash
source /Users/yellowstone/miniconda3/etc/profile.d/conda.sh
conda activate qlab
cd /Users/yellowstone/bangbae
uvicorn api.main:app --host 0.0.0.0 --port 8100 >> /Users/yellowstone/bangbae/logs/api.log 2>> /Users/yellowstone/bangbae/logs/api.err
