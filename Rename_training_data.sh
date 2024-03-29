#!/bin/bash
# f=$1
exp_name=$1
d="1"
echo $exp_name

# for generate train data
# num=3600
# for i in $(seq 1 10); 
# do
#     dir="./log/Render_datas/${exp_name}/${exp_name}_data_${i}/imgs_test_all"
#     echo $dir

#     mapfile files <<< "$(find "$dir" -maxdepth "$d" -type f -name '*.png' ! -type d -print0 | sort -zV | xargs -r0 )"
#     Allfiles=($files) 

#     for file in "${Allfiles[@]}"; do
#         file="$(tr -d '\n' <<< "$file")"
#         echo $file
#         mv -T $file ./log/Render_datas/${exp_name}/${exp_name}_data_${i}/imgs_test_all/${num}.png
#         ((num++))
#         echo $num
#     done
# done

## for formulate test data (cp?
num=1080
dir="./log/Render_datas/${exp_name}_data_4/imgs_test_all"
echo $dir

mapfile files <<< "$(find "$dir" -maxdepth "$d" -type f -name '*.png' ! -type d -print0 | sort -zV | xargs -r0 )"
Allfiles=($files) 

for file in "${Allfiles[@]}"; do
    file="$(tr -d '\n' <<< "$file")"
    echo $file
    mv -T $file ./log/Render_datas/${exp_name}_data_full/imgs_test_all/${num}.png
    ((num++))
    echo $num
done
