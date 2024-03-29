
import os
from cv2 import threshold
from tqdm.auto import tqdm
from opt import config_parser



import json, random
from renderer import *
from utils import *
from torch.utils.tensorboard import SummaryWriter
import datetime

from dataLoader import dataset_dict
import sys
import subprocess
import time
import shutil
import in_place



device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

renderer = OctreeRender_trilinear_fast
DEBUG = True
thres=5.8

class SimpleSampler:
    def __init__(self, total, batch):
        self.total = total
        self.batch = batch
        self.curr = total
        self.ids = None

    def nextids(self):
        self.curr+=self.batch
        if self.curr + self.batch > self.total:
            self.ids = torch.LongTensor(np.random.permutation(self.total))
            self.curr = 0
        return self.ids[self.curr:self.curr+self.batch]


@torch.no_grad()
def export_mesh(args):

    ckpt = torch.load(args.ckpt, map_location=device)
    kwargs = ckpt['kwargs']
    kwargs.update({'device': device})
    tensorf = eval(args.model_name)(**kwargs)
    tensorf.load(ckpt)

    alpha,_ = tensorf.getDenseAlpha()
    convert_sdf_samples_to_ply(alpha.cpu(), f'{args.ckpt[:-3]}.ply',bbox=tensorf.aabb.cpu(), level=0.005)


@torch.no_grad()
def render_test(args):
    # init dataset
    dataset = dataset_dict[args.dataset_name]
    test_dataset = dataset(args.datadir, split='test', downsample=args.downsample_train, is_stack=True)
    white_bg = test_dataset.white_bg
    ndc_ray = args.ndc_ray

    if not os.path.exists(args.ckpt):
        print('the ckpt path does not exists!!')
        return

    ckpt = torch.load(args.ckpt, map_location=device)
    kwargs = ckpt['kwargs']
    kwargs.update({'device': device})
    tensorf = eval(args.model_name)(**kwargs)
    tensorf.load(ckpt)

    logfolder = os.path.dirname(args.ckpt)
    if args.render_train:
        os.makedirs(f'{logfolder}/imgs_train_all', exist_ok=True)
        train_dataset = dataset(args.datadir, split='train', downsample=args.downsample_train, is_stack=True)
        PSNRs_test = evaluation(train_dataset,tensorf, args, renderer, f'{logfolder}/imgs_train_all/',
                    N_vis=-1, N_samples=-1, white_bg = white_bg, ndc_ray=ndc_ray, only_PSNR=args.only_PSNR ,device=device)
        print(f'======> {args.expname} train all psnr: {np.mean(PSNRs_test)} <========================')

    if args.render_test:
        print("render_test=================================")
        os.makedirs(f'{logfolder}/imgs_test_all', exist_ok=True)
        evaluation(test_dataset,tensorf, args, renderer, f'{logfolder}/imgs_test_all/', resPath=f'{logfolder}/{args.expname}_res/',
                N_vis=-1, N_samples=-1, white_bg = white_bg, ndc_ray=ndc_ray, only_PSNR=args.only_PSNR, device=device)


    if args.render_path:
        print("render_path=================================")
        c2ws = test_dataset.render_path
        os.makedirs(f'{logfolder}/imgs_path_all', exist_ok=True)
        evaluation_path(test_dataset,tensorf, c2ws, renderer, f'{logfolder}/imgs_path_all/', resPath=f'{logfolder}/{args.expname}_res/',
                                N_vis=-1, N_samples=-1, white_bg = white_bg, ndc_ray=ndc_ray,device=device)
        ## add camera pose
        if args.dataset_name == 'blender':
            for idx, c2w in enumerate(c2ws):
                c2ws[idx] = c2w @ torch.Tensor(np.array([[1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]]))
            render_poses_cpu = c2ws.cpu().numpy()
            np.save(os.path.join(f'{logfolder}/imgs_path_all', 'Camera_poses.npy'), render_poses_cpu)
        else: ## IDK dataset
            render_poses_cpu = c2ws
            np.save(os.path.join(f'{logfolder}/imgs_path_all', 'Camera_poses.npy'), render_poses_cpu)

## 0404 yue
@torch.no_grad()
def NextBView(args):
    if args.add_timestamp:
        logfolder = f'{args.basedir}/{args.expname}{datetime.datetime.now().strftime("-%Y%m%d-%H%M%S")}'
    else:
        logfolder = f'{args.basedir}/{args.NBV_routename}/{args.expname}'

    if args.render_test:
        File_path = f'{logfolder}/imgs_test_all'
    else:
        File_path = f'{logfolder}/imgs_path_all'

    # direct make results in this folder to lesson some labor work
    os.makedirs(f'{logfolder}/{args.expname}_res', exist_ok=True)
    Exp_path = f'{logfolder}/{args.expname}_res'
    ### NRIQA part
    time0 = time.time()
    if not os.path.exists(f'{Exp_path}/IQA_output.txt'):
        subprocess.run(f"./NRIQA_script.sh {File_path} {Exp_path}", shell=True)
        # shutil.copy2(f'{File_path}/output.txt', f'{File_path}/IQA_output.txt')
        # os.remove(f'{File_path}/output.txt')
    dt = time.time() - time0
    H, M, S = GetdeltaTime(dt)
    print(f"End NRIQA, with time: {H:d}:{M:02d}:{S:02d}")

    ### Depth Uncertainty Part
    time0 = time.time()
    if not os.path.exists(f'{Exp_path}/Depth_Errors.txt'):
        Imgs = [os.path.join(File_path, "rgbd", f) for f in sorted_alphanumeric(os.listdir(os.path.join(File_path, "rgbd"))) \
        if f.endswith('npz')]
        Size = np.load(Imgs[0])['depth'].shape
        Total_pixels = Size[0]*Size[1]

        depth_err_col = []
        for Img_nam in Imgs:
            depth = np.load(Img_nam)['depth']
            Error = np.abs(depth - 0.0) # diff near / 0.0 for llff
            N_Error = (Error < 0.05).sum() / Total_pixels  # normalize [0-1]
            depth_err_col.append(N_Error)
        depth_err_col = np.array(depth_err_col)
        print(depth_err_col.max())
        np.savetxt(os.path.join(Exp_path, 'Depth_Errors.txt'), depth_err_col, fmt='%.10f')
    dt = time.time() - time0
    H, M, S = GetdeltaTime(dt)
    print(f"End Depth Uncertainty, with time: {H:d}:{M:02d}:{S:02d}")


    ## Calculate Uncertainty (\alpha * NRIQA + \beta * Depth_Outliers)
    NRIQA = np.loadtxt(os.path.join(Exp_path, 'IQA_output.txt'))
    Raw_NRIQA = NRIQA.copy()
    Max_NRIQA = 10 ## NIMA
    NRIQA = Max_NRIQA - NRIQA # reverse to map uncertainty (higher is worse)
    NRIQA /= 9 # normalize [1-10] to [0-1]

    DO = np.loadtxt(os.path.join(Exp_path, 'Depth_Errors.txt'))
    alpha = 1/90
    beta = 89/90
    ##load now list to mask out overestimate or selected
    total_idx = np.arange(len(NRIQA))
    route_path = os.path.abspath(os.path.join(logfolder, os.pardir))
    now_list = np.loadtxt(os.path.join(route_path, 'Now_Views.txt'))
    mask_out = np.setdiff1d(total_idx, now_list)
    ## mask selected views
    NRIQA = NRIQA[mask_out]
    DO = DO[mask_out]

    test = (NRIQA*alpha+DO*beta)
    
    Bad_idx = np.where(test == test.max())[0][0]
    sg_view_num = mask_out[Bad_idx]
    if DEBUG:
        Bad_IQA_idx = np.where(NRIQA == NRIQA.max())[0][0]
        Bad_DO_idx = np.where(DO == DO.max())[0][0]
        sg_IQA_view = mask_out[Bad_IQA_idx]
        sg_DO_view = mask_out[Bad_DO_idx]

        Bad_IQA = Raw_NRIQA[sg_IQA_view] # Raw_NRIQA is not trimmed so use actually "idx" that look up from mask_out
        Bad_DO = DO[Bad_DO_idx] # DO has been trimmed so use the idx "where" find
        return sg_view_num, sg_IQA_view, sg_DO_view, Bad_IQA, Bad_DO
    else:
        return sg_view_num

def reconstruction(args):

    # init dataset
    dataset = dataset_dict[args.dataset_name]
    print(dataset)
    if args.dataset_name == 'llff':
        print(f"debug {args.llff_hold}")
        train_dataset = dataset(args.datadir, split='train', downsample=args.downsample_train, is_stack=False, hold_every=args.llff_hold)
        test_dataset = dataset(args.datadir, split='test', downsample=args.downsample_train, is_stack=True, hold_every=args.llff_hold)
    else:
        train_dataset = dataset(args.datadir, split='train', downsample=args.downsample_train, is_stack=False)
        test_dataset = dataset(args.datadir, split='test', downsample=args.downsample_train, is_stack=True)
    white_bg = train_dataset.white_bg
    near_far = train_dataset.near_far
    ndc_ray = args.ndc_ray

    # init resolution
    upsamp_list = args.upsamp_list
    update_AlphaMask_list = args.update_AlphaMask_list
    n_lamb_sigma = args.n_lamb_sigma
    n_lamb_sh = args.n_lamb_sh

    
    if args.add_timestamp:
        logfolder = f'{args.basedir}/{args.expname}{datetime.datetime.now().strftime("-%Y%m%d-%H%M%S")}'
    elif args.NBV_route:
        logfolder = f'{args.basedir}/{args.NBV_routename}/{args.expname}'
    else:
        logfolder = f'{args.basedir}/{args.expname}'
    

    # init log file
    os.makedirs(logfolder, exist_ok=True)
    os.makedirs(f'{logfolder}/imgs_vis', exist_ok=True)
    os.makedirs(f'{logfolder}/imgs_rgba', exist_ok=True)
    os.makedirs(f'{logfolder}/rgba', exist_ok=True)
    summary_writer = SummaryWriter(logfolder)



    # init parameters
    # tensorVM, renderer = init_parameters(args, train_dataset.scene_bbox.to(device), reso_list[0])
    aabb = train_dataset.scene_bbox.to(device)
    reso_cur = N_to_reso(args.N_voxel_init, aabb)
    nSamples = min(args.nSamples, cal_n_samples(reso_cur,args.step_ratio))


    if args.ckpt is not None:
        ckpt = torch.load(args.ckpt, map_location=device)
        kwargs = ckpt['kwargs']
        kwargs.update({'device':device})
        tensorf = eval(args.model_name)(**kwargs)
        tensorf.load(ckpt)
    else:
        tensorf = eval(args.model_name)(aabb, reso_cur, device,
                    density_n_comp=n_lamb_sigma, appearance_n_comp=n_lamb_sh, app_dim=args.data_dim_color, near_far=near_far,
                    shadingMode=args.shadingMode, alphaMask_thres=args.alpha_mask_thre, density_shift=args.density_shift, distance_scale=args.distance_scale,
                    pos_pe=args.pos_pe, view_pe=args.view_pe, fea_pe=args.fea_pe, featureC=args.featureC, step_ratio=args.step_ratio, fea2denseAct=args.fea2denseAct)


    grad_vars = tensorf.get_optparam_groups(args.lr_init, args.lr_basis)
    if args.lr_decay_iters > 0:
        lr_factor = args.lr_decay_target_ratio**(1/args.lr_decay_iters)
    else:
        args.lr_decay_iters = args.n_iters
        lr_factor = args.lr_decay_target_ratio**(1/args.n_iters)

    print("lr decay", args.lr_decay_target_ratio, args.lr_decay_iters)
    
    optimizer = torch.optim.Adam(grad_vars, betas=(0.9,0.99))


    #linear in logrithmic space
    N_voxel_list = (torch.round(torch.exp(torch.linspace(np.log(args.N_voxel_init), np.log(args.N_voxel_final), len(upsamp_list)+1))).long()).tolist()[1:]


    torch.cuda.empty_cache()
    PSNRs,PSNRs_test = [],[0]

    allrays, allrgbs = train_dataset.all_rays, train_dataset.all_rgbs
    if not args.ndc_ray:
        allrays, allrgbs = tensorf.filtering_rays(allrays, allrgbs, bbox_only=True)
    trainingSampler = SimpleSampler(allrays.shape[0], args.batch_size)

    Ortho_reg_weight = args.Ortho_weight
    print("initial Ortho_reg_weight", Ortho_reg_weight)

    L1_reg_weight = args.L1_weight_inital
    print("initial L1_reg_weight", L1_reg_weight)
    TV_weight_density, TV_weight_app = args.TV_weight_density, args.TV_weight_app
    tvreg = TVLoss()
    print(f"initial TV_weight density: {TV_weight_density} appearance: {TV_weight_app}")


    pbar = tqdm(range(args.n_iters), miniters=args.progress_refresh_rate, file=sys.stdout)
    for iteration in pbar:


        ray_idx = trainingSampler.nextids()
        rays_train, rgb_train = allrays[ray_idx], allrgbs[ray_idx].to(device)

        #rgb_map, alphas_map, depth_map, weights, uncertainty
        rgb_map, alphas_map, depth_map, weights, uncertainty = renderer(rays_train, tensorf, chunk=args.batch_size,
                                N_samples=nSamples, white_bg = white_bg, ndc_ray=ndc_ray, device=device, is_train=True)

        loss = torch.mean((rgb_map - rgb_train) ** 2)


        # loss
        total_loss = loss
        if Ortho_reg_weight > 0:
            loss_reg = tensorf.vector_comp_diffs()
            total_loss += Ortho_reg_weight*loss_reg
            summary_writer.add_scalar('train/reg', loss_reg.detach().item(), global_step=iteration)
        if L1_reg_weight > 0:
            loss_reg_L1 = tensorf.density_L1()
            total_loss += L1_reg_weight*loss_reg_L1
            summary_writer.add_scalar('train/reg_l1', loss_reg_L1.detach().item(), global_step=iteration)

        if TV_weight_density>0:
            TV_weight_density *= lr_factor
            loss_tv = tensorf.TV_loss_density(tvreg) * TV_weight_density
            total_loss = total_loss + loss_tv
            summary_writer.add_scalar('train/reg_tv_density', loss_tv.detach().item(), global_step=iteration)
        if TV_weight_app>0:
            TV_weight_app *= lr_factor
            # loss_tv = loss_tv + tensorf.TV_loss_app(tvreg)*TV_weight_app
            loss_tv = tensorf.TV_loss_app(tvreg)*TV_weight_app
            total_loss = total_loss + loss_tv
            summary_writer.add_scalar('train/reg_tv_app', loss_tv.detach().item(), global_step=iteration)

        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

        loss = loss.detach().item()
        
        PSNRs.append(-10.0 * np.log(loss) / np.log(10.0))
        summary_writer.add_scalar('train/PSNR', PSNRs[-1], global_step=iteration)
        summary_writer.add_scalar('train/mse', loss, global_step=iteration)


        for param_group in optimizer.param_groups:
            param_group['lr'] = param_group['lr'] * lr_factor

        # Print the current values of the losses.
        if iteration % args.progress_refresh_rate == 0:
            pbar.set_description(
                f'Iteration {iteration:05d}:'
                + f' train_psnr = {float(np.mean(PSNRs)):.2f}'
                + f' test_psnr = {float(np.mean(PSNRs_test)):.2f}'
                + f' mse = {loss:.6f}'
            )
            PSNRs = []


        if iteration % args.vis_every == args.vis_every - 1 and args.N_vis!=0:
            PSNRs_test = evaluation(test_dataset,tensorf, args, renderer, f'{logfolder}/imgs_vis/', N_vis=args.N_vis,
                    prtx=f'{iteration:06d}_', N_samples=nSamples, white_bg = white_bg, ndc_ray=ndc_ray, compute_extra_metrics=False, only_PSNR=args.only_PSNR)
            summary_writer.add_scalar('test/psnr', np.mean(PSNRs_test), global_step=iteration)



        if iteration in update_AlphaMask_list:

            if reso_cur[0] * reso_cur[1] * reso_cur[2]<256**3:# update volume resolution
                reso_mask = reso_cur
            new_aabb = tensorf.updateAlphaMask(tuple(reso_mask))
            if iteration == update_AlphaMask_list[0]:
                tensorf.shrink(new_aabb)
                # tensorVM.alphaMask = None
                L1_reg_weight = args.L1_weight_rest
                print("continuing L1_reg_weight", L1_reg_weight)


            if not args.ndc_ray and iteration == update_AlphaMask_list[1]:
                # filter rays outside the bbox
                allrays,allrgbs = tensorf.filtering_rays(allrays,allrgbs)
                trainingSampler = SimpleSampler(allrgbs.shape[0], args.batch_size)


        if iteration in upsamp_list:
            n_voxels = N_voxel_list.pop(0)
            reso_cur = N_to_reso(n_voxels, tensorf.aabb)
            nSamples = min(args.nSamples, cal_n_samples(reso_cur,args.step_ratio))
            tensorf.upsample_volume_grid(reso_cur)

            if args.lr_upsample_reset:
                print("reset lr to initial")
                lr_scale = 1 #0.1 ** (iteration / args.n_iters)
            else:
                lr_scale = args.lr_decay_target_ratio ** (iteration / args.n_iters)
            grad_vars = tensorf.get_optparam_groups(args.lr_init*lr_scale, args.lr_basis*lr_scale)
            optimizer = torch.optim.Adam(grad_vars, betas=(0.9, 0.99))
        

    tensorf.save(f'{logfolder}/{args.expname}.th')


    if args.render_train:
        os.makedirs(f'{logfolder}/imgs_train_all', exist_ok=True)
        train_dataset = dataset(args.datadir, split='train', downsample=args.downsample_train, is_stack=True)
        PSNRs_test = evaluation(train_dataset,tensorf, args, renderer, f'{logfolder}/imgs_train_all/',
                    N_vis=-1, N_samples=-1, white_bg = white_bg, ndc_ray=ndc_ray, only_PSNR=args.only_PSNR, device=device)
        print(f'======> {args.expname} test all psnr: {np.mean(PSNRs_test)} <========================')

    if args.render_test:
        os.makedirs(f'{logfolder}/imgs_test_all', exist_ok=True)
        PSNRs_test = evaluation(test_dataset,tensorf, args, renderer, f'{logfolder}/imgs_test_all/', resPath=f'{logfolder}/{args.expname}_res/',
                    N_vis=-1, N_samples=-1, white_bg = white_bg, ndc_ray=ndc_ray, only_PSNR=args.only_PSNR, device=device)
        summary_writer.add_scalar('test/psnr_all', np.mean(PSNRs_test), global_step=iteration)
        print(f'======> {args.expname} test all psnr: {np.mean(PSNRs_test)} <========================')
        logger.info(f'======> {args.expname} test all psnr: {np.mean(PSNRs_test)} <========================')

    if args.render_path:
        c2ws = test_dataset.render_path
        # c2ws = test_dataset.poses
        print('========>',c2ws.shape)
        os.makedirs(f'{logfolder}/imgs_path_all', exist_ok=True)
        evaluation_path(test_dataset,tensorf, c2ws, renderer, f'{logfolder}/imgs_path_all/', resPath=f'{logfolder}/{args.expname}_res/',
                                N_vis=-1, N_samples=-1, white_bg = white_bg, ndc_ray=ndc_ray,device=device)
        ## add camera pose
        if args.dataset_name == 'blender':
            for idx, c2w in enumerate(c2ws):
                c2ws[idx] = c2w @ torch.Tensor(np.array([[1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]]))
            render_poses_cpu = c2ws.cpu().numpy()
            np.save(os.path.join(f'{logfolder}/imgs_path_all', 'Camera_poses.npy'), render_poses_cpu)
        else: ## IDK dataset
            render_poses_cpu = c2ws
            np.save(os.path.join(f'{logfolder}/imgs_path_all', 'Camera_poses.npy'), render_poses_cpu)

    ## for cd list
    # test_c2ws = test_dataset.poses
    # if args.dataset_name == 'blender':
    #     solution = []
    #     for idx, c2w in enumerate(test_c2ws):
    #         test_c2ws[idx] = c2w @ torch.Tensor(np.array([[1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]]))
    #     test_poses_cpu = test_c2ws.cpu().numpy()
    #     myset = test_poses_cpu[:, 0:3, 3].copy()

    #     cd_folder = f'{args.basedir}/{args.NBV_routename}'
    #     now_poses = np.loadtxt(os.path.join(f'{cd_folder}', 'Now_Views.txt'))
    #     now_poses = now_poses[2:]

    #     for idx in now_poses:
    #         solution.append(myset[int(idx)])
    #     solution = np.asarray(solution)
    #     # print(solution)
    #     max_id = cdist(myset, solution, 'euclidean').sum(1).argmax()
    #     # max_pt=myset[max_id]
    #     return max_id


if __name__ == '__main__':

    torch.set_default_dtype(torch.float32)
    torch.manual_seed(20211202)
    np.random.seed(20211202)

    args = config_parser()
    # print(args)
    File_path = f'{args.basedir}/{args.NBV_routename}'
    os.makedirs(File_path, exist_ok=True)

    ## logging setting
    logger = logging.getLogger('NBV_logger')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(os.path.join(f'{File_path}', f'Experiment.log'))
    handler.addFilter(MyFilter(logging.INFO))
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # logging.basicConfig(filename=os.path.join(f'{File_path}', f'Experiment.log'), filemode='a', level=logging.INFO)
    logger.addHandler(handler)
    #############################

    logger.info(f'=============> {args.expname} <===============')

    if args.export_mesh:
        export_mesh(args)
    if not args.only_NBV:
        if args.render_only and (args.render_test or args.render_path):
            render_test(args)
        else:
            # cd_max_id = reconstruction(args)
            reconstruction(args)
    
    ## control NBV -> Image Uncertainty + Depth Uncertainty
    if args.NBV_route:
        ## replace exp_name for next NBV iteration
        new_exp = args.expname.split('_')
        new_num = int(new_exp[-1])+1
        new_exp[-1] = str(new_num)
        with in_place.InPlace(args.config) as file:
            for line in file:
                line = line.replace(args.expname, '_'.join(new_exp))
                file.write(line)
                
        if DEBUG:
            suggest, sg_IQA, sg_DO, IQA_val, DO_val = NextBView(args)
            print(f"Suggest NBV by ALL is #{suggest}")
            print(f"Suggest NBV by NRIQA is #{sg_IQA}, and min quality value is {IQA_val}, convert PSNR = {inv_Rescale(IQA_val)}")
            print(f"Suggest NBV by DO is #{sg_DO}, and max DO value is {DO_val}")
            if IQA_val >= thres:
                print(f"NBV route reach the terminal threshold {thres}")

            
            logger.info(f"Suggest NBV by ALL is #{suggest}")
            logger.info(f"Suggest NBV by NRIQA is #{sg_IQA}, and min quality value is {IQA_val}, convert PSNR = {inv_Rescale(IQA_val)}")
            logger.info(f"Suggest NBV by DO is #{sg_DO}, and max DO value is {DO_val}\n")
            # logger.info("\n")

            Next_idx = sg_IQA
            ##for auto add nbv
            # subprocess.run(f"python add_NBV.py --config {args.config} --add_view {Next_idx}", shell=True)
            # print(f"Auto add NBV {Next_idx} to {args.config} finished !!!")
        else:
            suggest = NextBView(args)
            print(f"Suggest NBV by ALL is #{suggest}")

