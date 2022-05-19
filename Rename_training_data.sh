#!/bin/bash
# f=$1
exp_name=$1
d="1"
# echo $f
echo $exp_name
# name="lego_data_${f}"
# mkdir -p ./log/Render_datas/${exp_name}
# mv -T ./log/Render_datas/${exp_name}_data ./log/Render_datas/${exp_name}/${exp_name}_data_${f}
# mv -T ./log/Render_datas/$exp_name ./log/Render_datas/${exp_name}_${f}

num=21600
for i in $(seq 1 10); 
do
    # implement your logic here
    dir="./log/Render_datas/${exp_name}/${exp_name}_data_${i}/imgs_test_all"
    echo $dir
    # python3 add_NBV.py --config $f --delete_all 1
    # python3 add_NBV.py --config $f --add_shuffle_views $i
    # python3 train.py --config $f --NBV_route 1 --render_test 1
    mapfile files <<< "$(find "$dir" -maxdepth "$d" -type f -name '*.png' ! -type d -print0 | sort -z | xargs -r0 )"
    Allfiles=($files) 

    for file in "${Allfiles[@]}"; do
        file="$(tr -d '\n' <<< "$file")"
        echo $file
        mv -T $file ./log/Render_datas/${exp_name}/${exp_name}_data_${i}/imgs_test_all/${num}.png
        ((num++))
        echo $num
    done
done