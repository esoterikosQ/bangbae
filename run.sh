#!/bin/bash
source /Users/yellowstone/miniconda3/etc/profile.d/conda.sh
conda activate qlab
cd /Users/yellowstone/bangbae
python bot.py >> /Users/yellowstone/bangbae/logs/bot.log 2>> /Users/yellowstone/bangbae/logs/bot.err
