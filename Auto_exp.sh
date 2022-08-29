#!/bin/bash
f=$1
echo $f
for i in $(seq 1 11); 
do
    # implement your logic here
    python3 train.py --config $f --NBV_route 1 --render_test 1
    # mv -T ./log/Render_datas/${exp_name}_data ./log/Render_datas/${exp_name}/${exp_name}_data_${i}

done