import numpy as np
import cv2 as cv
import os
import json
from opt import config_parser

if __name__ == '__main__':
    args = config_parser()

    ## read json and add NBV
    if args.add_view or args.add_shuffle_views:
        Data_dir = args.datadir
        spdir = Data_dir.split("/")
        Source_file = f"Render_Specify_views_{spdir[-1]}/transforms_train"
        Target_file = "transforms_train"
        File_path = f'{args.basedir}/{args.NBV_routename}'
        os.makedirs(f'{File_path}', exist_ok=True)
        ##  database
        with open(os.path.join(Data_dir, f'{Source_file}.json'), 'r') as soucefp:
            meta = json.load(soucefp)

        ## original set
        with open(os.path.join(Data_dir, f'{Target_file}.json'), 'r') as targetfp:
            target = json.load(targetfp)
        
        # now list must be load in and write out
        if not os.path.exists(f'{File_path}/Now_Views.txt'):
            with open(os.path.join(f'{File_path}', 'Now_Views.txt'), "a") as file:
                np.savetxt(file, [-1, -1], fmt='%d')
                file.close()
        now_list = np.loadtxt(os.path.join(f'{File_path}', 'Now_Views.txt'))
        
        ## add_shuffle_views
        if args.add_shuffle_views:
            # np.random.seed(10)
            layer_1 = np.random.choice(np.arange(0, 80), 1, replace=False)
            layer_2 = np.random.choice(np.arange(80, 160), 2, replace=False)
            layer_3 = np.random.choice(np.arange(160, 240), 3, replace=False)
            layer_4 = np.random.choice(np.arange(240, 360), 4, replace=False)
            all_layer = np.concatenate([layer_1, layer_2, layer_3, layer_4])
            t_shuffle = np.random.permutation(all_layer)
            target_list = t_shuffle[:args.add_shuffle_views]
        else:
            target_list = [args.add_view]

        ## append then together
        for i in target_list:
            print(i)
            if i in now_list:
                print(f'view {i} already in views set!!!')
                continue
            target['frames'].append(meta['frames'][i])
            now_list = np.concatenate((now_list, [i]))
            print(now_list)

        ## write to original file
        with open(os.path.join(Data_dir, f'{Target_file}.json'), 'w') as targetfp:
            json.dump(target, targetfp, indent = 4)
        np.savetxt(os.path.join(f'{File_path}', 'Now_Views.txt'), now_list, fmt='%d')

    if args.delete_all:
        Data_dir = args.datadir
        File_path = f'{args.basedir}/{args.NBV_routename}'
        Target_file = "transforms_train"
        if os.path.exists(f'{File_path}/Now_Views.txt'):
            os.remove(f'{File_path}/Now_Views.txt')
            print(f"Found list in {File_path} and remove it!!!!")
        
        ## original set
        with open(os.path.join(Data_dir, f'{Target_file}.json'), 'r') as targetfp:
            target = json.load(targetfp)
        ## remove all views
        target['frames'] = []
        with open(os.path.join(Data_dir, f'{Target_file}.json'), 'w') as targetfp:
            json.dump(target, targetfp, indent = 4)
        print(f"remove training set at {Data_dir}/{Target_file}")