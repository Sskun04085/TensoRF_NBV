#!/bin/bash

exp_name=$1
d="1"
# echo $f
echo $exp_name

# for training data
# for i in $(seq 1 10); 
# do
#     # implement your logic here
#     # dir="./datasets/NeRF_datasets/NeRF_images/${exp_name}/${exp_name}_data_${i}/imgs_test_all"
#     dir="./log/Render_datas/${exp_name}/${exp_name}_data_${i}/imgs_test_all"
#     # echo $dir

#     mapfile files <<< "$(find "$dir" -maxdepth "$d" -type f -name '*.png' ! -type d -print0 | sort -zV | xargs -r0 )"
#     Allfiles=($files) 

#     for file in "${Allfiles[@]}"; do
#         file="$(tr -d '\n' <<< "$file")"
#         # echo $file
#         cp $file ./datasets/NeRF_datasets/NeRF_images
#     done
# done

##for testing data


dir="./log/Render_datas/${exp_name}_data_full/imgs_test_all"
echo $dir

mapfile files <<< "$(find "$dir" -maxdepth "$d" -type f -name '*.png' ! -type d -print0 | sort -zV | xargs -r0 )"
Allfiles=($files) 

for file in "${Allfiles[@]}"; do
    file="$(tr -d '\n' <<< "$file")"
    # echo $file
    cp $file ./datasets/NeRF_datasets/NeRF_test_ship_rabbit
done
