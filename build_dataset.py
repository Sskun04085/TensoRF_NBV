import numpy as np
import cv2 as cv
import os
import pickle
import pandas as pd
import math
import random

def Rescale(in_array, omin=5, omax=45, nmin=1, nmax=10):
    old_range = omax-omin
    new_range = nmax-nmin
    return ((in_array-omin) * new_range / old_range) + nmin

target_dir = "./log/Render_datas"
# datasets_type = os.listdir(target_dir)
# datasets_type = ['lego', 'chair', 'drums', 'ficus', 'hotdog', 'materials', 'mic']
datasets_type = ['lego', 'chair']

img_names = []
PSNR_cols = np.array([])
firstIter = True

for name in datasets_type:
    for i in range(1, 11):
        path = target_dir + f"/{name}/{name}_data_{i}/imgs_test_all"
        img_names += [f for f in sorted(os.listdir(path)) if f.endswith('png')]
        if firstIter:
            PSNR_cols = np.loadtxt(path+'/test_views_PSNR.txt')
            firstIter = False
        else:
            PSNR_cols = np.concatenate([PSNR_cols, np.loadtxt(path+'/test_views_PSNR.txt')])
print(PSNR_cols)


test_csv = "./test.csv"
columns = ['img_name', 'MOS', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'c10']

tmp_dist = []
tmp_img = []
for idx, v in enumerate(PSNR_cols):
    n_class = np.zeros(10, dtype=int)
    R_v = Rescale(np.clip(v, 5, 45))
    n_dist = np.clip(np.around(np.random.normal(R_v, 0.5, 100)), 1, 10)
    unique, counts = np.unique(n_dist, return_counts=True)
    n_dict = dict(zip(unique, counts))
    for key, value in n_dict.items():
        n_class[int(key)-1] = value
    tmp_dist.append(n_class)
    
df = pd.DataFrame(img_names)
# print(df)
df2 = pd.DataFrame(PSNR_cols)
# print(df2)
df3 = pd.DataFrame(tmp_dist)
# print(df3)
dfa = pd.concat([df, df2, df3], axis=1)
dfa.columns = columns
# print(dfa)
dfa.to_csv(test_csv, index=False)