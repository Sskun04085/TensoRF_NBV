import numpy as np
import cv2 as cv
import os
import re
import pickle
import pandas as pd
import math
import random
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test_name', type=str, default=None)
    parser.add_argument('--append_data', type=int, default=None)
    args = parser.parse_args()
    return args

def Rescale(in_array, omin=5, omax=45, nmin=1, nmax=10):
    old_range = omax-omin
    new_range = nmax-nmin
    return ((in_array-omin) * new_range / old_range) + nmin

def sorted_alphanumeric(data):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(data, key=alphanum_key)

def main(args):
    target_dir = "./log/Render_datas"
    ## only test data
    if args.test_name:
        # dir_name = os.listdir(target_dir)
        dir_name = ['ship_data_full', 'rabbit_data_full', 'ship_data_1', 'rabbit_data_4']

        img_names = []
        PSNR_cols = np.array([])
        firstIter = True

        ## get corresponding value metric(e.g. PSNR)
        for name in dir_name:
            path = target_dir + f"/{name}/imgs_test_all"
            img_names += [f for f in sorted_alphanumeric(os.listdir(path)) if f.endswith('png')]
            if firstIter:
                PSNR_cols = np.loadtxt(path+'/test_views_PSNR.txt')
                firstIter = False
            else:
                PSNR_cols = np.concatenate([PSNR_cols, np.loadtxt(path+'/test_views_PSNR.txt')])

        # save dir
        os.makedirs("./datasets/meta_info", exist_ok=True)
        os.makedirs("./datasets/train_split_info", exist_ok=True)
        ## change name here!!!!!!!
        test_csv = f"./datasets/meta_info/{args.test_name}.csv"
        split_file = f"./datasets/train_split_info/{args.test_name}_split.pkl"
        columns = ['img_name', 'MOS', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'c10']

        if not args.append_data:
            ## for split file {only test}
            arr = np.arange(len(PSNR_cols))
            split = {}
            split[1] = {'test':arr}

            with open(split_file, 'wb') as handle:
                pickle.dump(split, handle, protocol=pickle.HIGHEST_PROTOCOL)

    ## formulate all data type
    else:
        # datasets_type = os.listdir(target_dir)
        datasets_type = ['ship', 'rabbit']
        # datasets_type = ['chair']

        img_names = []
        PSNR_cols = np.array([])
        firstIter = True

        ## get corresponding value metric(e.g. PSNR)
        ## [1-11] : for 10 loop and [11] : for full training data
        for name in datasets_type:
            for i in range(1, 12):
                path = target_dir + f"/{name}/{name}_data_{i}/imgs_test_all"
                img_names += [f for f in sorted_alphanumeric(os.listdir(path)) if f.endswith('png')]
                if firstIter:
                    PSNR_cols = np.loadtxt(path+'/test_views_PSNR.txt')
                    firstIter = False
                else:
                    PSNR_cols = np.concatenate([PSNR_cols, np.loadtxt(path+'/test_views_PSNR.txt')])

        # save dir
        os.makedirs("./datasets/meta_info", exist_ok=True)
        os.makedirs("./datasets/train_split_info", exist_ok=True)
        ## change name here!!!!!!!
        test_csv = "./datasets/meta_info/NeRF_test_ship_rabbit.csv"
        split_file = "./datasets/train_split_info/test_ship_rabbit.pkl"
        columns = ['img_name', 'MOS', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'c10']

        if not args.append_data:
            ## for split file
            # val_size = int(len(PSNR_cols)/10)
            # arr = np.arange(len(PSNR_cols))
            # np.random.shuffle(arr)
            # split = {}
            # split[1] = {'train':arr[:-val_size], 'val':arr[-val_size:]}

            # with open(split_file, 'wb') as handle:
            #     pickle.dump(split, handle, protocol=pickle.HIGHEST_PROTOCOL)
            
            ## for split file {only test}
            arr = np.arange(len(PSNR_cols))
            split = {}
            split[1] = {'test':arr}

            with open(split_file, 'wb') as handle:
                pickle.dump(split, handle, protocol=pickle.HIGHEST_PROTOCOL)

    # below is for NIMA model
    tmp_dist = []
    tmp_Rv = []
    for idx, v in enumerate(PSNR_cols):
        # class range for NIMA model
        n_class = np.zeros(10, dtype=int)
        # assume min PSNR 5, max PSNR 45 , clip to this range
        R_v = Rescale(np.clip(v, 5, 45))
        n_dist = np.clip(np.around(np.random.normal(R_v, 0.5, 100)), 1, 10)
        unique, counts = np.unique(n_dist, return_counts=True)
        n_dict = dict(zip(unique, counts))
        for key, value in n_dict.items():
            n_class[int(key)-1] = value
        tmp_dist.append(n_class)
        tmp_Rv.append(R_v)
        
    df = pd.DataFrame(img_names)
    # print(df)
    df2 = pd.DataFrame(tmp_Rv)
    # print(df2)
    df3 = pd.DataFrame(tmp_dist)
    # print(df3)
    dfa = pd.concat([df, df2, df3], axis=1)
    dfa.columns = columns
    # print(dfa)
    dfa.to_csv(test_csv, index=False)

if __name__ == '__main__':
    args = parse_args()
    main(args)