#!/bin/bash
f=$1
dir=$2

echo $f
# python3 ~/CONTRIQUE/demo_score.py --im_path $f --model_path ~/CONTRIQUE/models/CONTRIQUE_checkpoint25.tar --linear_regressor_path ~/CONTRIQUE/models/CLIVE.save
# python3 /mnt/data2/jyyue/IQA-PyTorch/inference_iqa.py -n nima --model_path /mnt/data2/jyyue/IQA-PyTorch/pretrained/NeRF_full_best.pth -i $f --save_file ${f}/IQA_output.txt
python3 /mnt/data2/jyyue/IQA-PyTorch/inference_iqa.py -n dbcnn --model_path /mnt/data2/jyyue/IQA-PyTorch/pretrained/DBCNN/DBCNN_NeRF.pth -i $f --save_file ${dir}/IQA_output.txt
# done



