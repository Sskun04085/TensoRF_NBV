#!/bin/bash
f=$1
# d="1"
# mapfile files <<< "$(find "$f" -maxdepth "$d" -type f -name '*.png' ! -type d -print0 | sort -z | xargs -r0 )"
# Allfiles=($files) 

# for file in "${Allfiles[@]}"; do
#     file="$(tr -d '\n' <<< "$file")"
    # implement your logic here
echo $f
python3 ../CONTRIQUE/demo_score.py --im_path $f --model_path ../CONTRIQUE/models/CONTRIQUE_checkpoint25.tar --linear_regressor_path ../CONTRIQUE/models/LIVE.save

# done



