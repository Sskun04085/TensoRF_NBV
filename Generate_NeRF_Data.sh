#!/bin/bash
f=$1
exp_name=$2
# d="1"
# mapfile files <<< "$(find "$f" -maxdepth "$d" -type f -name '*.png' ! -type d -print0 | sort -z | xargs -r0 )"
# Allfiles=($files) 
mkdir -p ./log/Render_datas/${exp_name}
for i in $(seq 1 10); 
do
    # implement your logic here
    echo $f
    python3 add_NBV.py --config $f --delete_all 1
    python3 add_NBV.py --config $f --add_shuffle_views $i
    python3 train.py --config $f --NBV_route 1 --render_test 1
    mv -T ./log/Render_datas/${exp_name}_data ./log/Render_datas/${exp_name}/${exp_name}_data_${i}

done



