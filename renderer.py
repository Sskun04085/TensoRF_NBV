import torch,os,imageio,sys
from tqdm.auto import tqdm
from dataLoader.ray_utils import get_rays
from models.tensoRF import TensorVM, TensorCP, raw2alpha, TensorVMSplit, AlphaGridMask
from utils import *
from dataLoader.ray_utils import ndc_rays_blender


def OctreeRender_trilinear_fast(rays, tensorf, chunk=4096, N_samples=-1, ndc_ray=False, white_bg=True, is_train=False, device='cuda'):

    rgbs, alphas, depth_maps, weights, uncertainties = [], [], [], [], []
    N_rays_all = rays.shape[0]
    for chunk_idx in range(N_rays_all // chunk + int(N_rays_all % chunk > 0)):
        rays_chunk = rays[chunk_idx * chunk:(chunk_idx + 1) * chunk].to(device)
    
        rgb_map, depth_map = tensorf(rays_chunk, is_train=is_train, white_bg=white_bg, ndc_ray=ndc_ray, N_samples=N_samples)

        rgbs.append(rgb_map)
        depth_maps.append(depth_map)
    
    return torch.cat(rgbs), None, torch.cat(depth_maps), None, None

@torch.no_grad()
def evaluation(test_dataset,tensorf, args, renderer, savePath=None, resPath=None, N_vis=5, prtx='', N_samples=-1,
               white_bg=False, ndc_ray=False, compute_extra_metrics=True, only_PSNR=0, device='cuda'):
    PSNRs, rgb_maps, depth_maps = [], [], []
    ssims,l_alex,l_vgg=[],[],[]
    os.makedirs(savePath, exist_ok=True)
    os.makedirs(savePath+"/rgbd", exist_ok=True)
    if resPath is not None:
        os.makedirs(resPath, exist_ok=True)

    try:
        tqdm._instances.clear()
    except Exception:
        pass

    near_far = test_dataset.near_far
    img_eval_interval = 1 if N_vis < 0 else max(test_dataset.all_rays.shape[0] // N_vis,1)
    idxs = list(range(0, test_dataset.all_rays.shape[0], img_eval_interval))
    for idx, samples in tqdm(enumerate(test_dataset.all_rays[0::img_eval_interval]), file=sys.stdout):
        print(idx)
        W, H = test_dataset.img_wh
        rays = samples.view(-1,samples.shape[-1])

        rgb_map, _, depth_map, _, _ = renderer(rays, tensorf, chunk=4096, N_samples=N_samples,
                                        ndc_ray=ndc_ray, white_bg = white_bg, device=device)
        rgb_map = rgb_map.clamp(0.0, 1.0)

        rgb_map, depth_map = rgb_map.reshape(H, W, 3).cpu(), depth_map.reshape(H, W).cpu()

        ## no need to vis depth map
        # depth_map, _ = visualize_depth_numpy(depth_map.numpy(),near_far)
        if len(test_dataset.all_rgbs):
            gt_rgb = test_dataset.all_rgbs[idxs[idx]].view(H, W, 3)
            loss = torch.mean((rgb_map - gt_rgb) ** 2)
            PSNRs.append(-10.0 * np.log(loss.item()) / np.log(10.0))

            if compute_extra_metrics:
                ssim = rgb_ssim(rgb_map, gt_rgb, 1)
                # l_a = rgb_lpips(gt_rgb.numpy(), rgb_map.numpy(), 'alex', tensorf.device)
                l_v = rgb_lpips(gt_rgb.numpy(), rgb_map.numpy(), 'vgg', tensorf.device)
                ssims.append(ssim)
                # l_alex.append(l_a)
                l_vgg.append(l_v)

        rgb_map = (rgb_map.numpy() * 255).astype('uint8')
        depth_map = depth_map.numpy()
        ##
        # rgb_map = np.concatenate((rgb_map, depth_map), axis=1)
        rgb_maps.append(rgb_map)
        depth_maps.append(depth_map)
        if savePath is not None and not only_PSNR:
            imageio.imwrite(f'{savePath}/{prtx}{idx:03d}.png', rgb_map)
            # rgb_map = np.concatenate((rgb_map, depth_map), axis=1)
            # imageio.imwrite(f'{savePath}/rgbd/{prtx}{idx:03d}.png', depth_map)
            np.savez(f'{savePath}/rgbd/{prtx}{idx:03d}.npz', depth=depth_map)
            
    ##  for only uniform camera, reorder maps only for better visulization(video output) excluding llff
    if N_vis < 0 and args.dataset_name != 'llff':
        f_0 = np.arange(0, 360, 8)
        for i in range(1, 8):
            f = np.arange(i, 360, 8)
            f_0 = np.concatenate((f_0, f))
        vis_rgb_maps = [rgb_maps[i] for i in f_0]
        vis_depth_maps = [depth_maps[i] for i in f_0]
    else:
        vis_rgb_maps = rgb_maps
        vis_depth_maps = depth_maps
        
    if not only_PSNR:
        imageio.mimwrite(f'{savePath}/{prtx}video.mp4', np.stack(vis_rgb_maps), fps=30, quality=10)
        imageio.mimwrite(f'{savePath}/{prtx}depthvideo.mp4', np.stack(vis_depth_maps), fps=30, quality=10)

    saveDirPath = resPath if resPath is not None else savePath
    if PSNRs:
        psnr = np.mean(np.asarray(PSNRs))
        if compute_extra_metrics:
            ssim = np.mean(np.asarray(ssims))
            # l_a = np.mean(np.asarray(l_alex))
            l_v = np.mean(np.asarray(l_vgg))
            np.savetxt(f'{saveDirPath}/{prtx}mean.txt', np.asarray([psnr, ssim, l_v]))
        else:
            np.savetxt(f'{saveDirPath}/{prtx}mean.txt', np.asarray([psnr]))
            
        np.savetxt(f'{saveDirPath}/test_views_PSNR.txt', np.asarray(PSNRs))
        np.savetxt(f'{saveDirPath}/test_views_ssim.txt', np.asarray(ssims))
        np.savetxt(f'{saveDirPath}/test_views_LPIPS_vgg.txt', np.asarray(l_vgg))


    return PSNRs

@torch.no_grad()
def evaluation_path(test_dataset,tensorf, c2ws, renderer, savePath=None, resPath=None, N_vis=5, prtx='', N_samples=-1,
                    white_bg=False, ndc_ray=False, compute_extra_metrics=True, device='cuda'):
    PSNRs, rgb_maps, depth_maps = [], [], []
    ssims,l_alex,l_vgg=[],[],[]
    os.makedirs(savePath, exist_ok=True)
    os.makedirs(savePath+"/rgbd", exist_ok=True)
    if resPath is not None:
        os.makedirs(resPath, exist_ok=True)

    try:
        tqdm._instances.clear()
    except Exception:
        pass

    near_far = test_dataset.near_far
    for idx, c2w in tqdm(enumerate(c2ws)):
        print(idx)
        W, H = test_dataset.img_wh

        c2w = torch.FloatTensor(c2w)
        rays_o, rays_d = get_rays(test_dataset.directions, c2w)  # both (h*w, 3)
        if ndc_ray:
            rays_o, rays_d = ndc_rays_blender(H, W, test_dataset.focal[0], 1.0, rays_o, rays_d)
        rays = torch.cat([rays_o, rays_d], 1)  # (h*w, 6)

        rgb_map, _, depth_map, _, _ = renderer(rays, tensorf, chunk=8192, N_samples=N_samples,
                                        ndc_ray=ndc_ray, white_bg = white_bg, device=device)
        rgb_map = rgb_map.clamp(0.0, 1.0)

        rgb_map, depth_map = rgb_map.reshape(H, W, 3).cpu(), depth_map.reshape(H, W).cpu()

        # depth_map, _ = visualize_depth_numpy(depth_map.numpy(),near_far)

        rgb_map = (rgb_map.numpy() * 255).astype('uint8')
        depth_map = depth_map.numpy()
        # rgb_map = np.concatenate((rgb_map, depth_map), axis=1)
        rgb_maps.append(rgb_map)
        depth_maps.append(depth_map)
        if savePath is not None:
            imageio.imwrite(f'{savePath}/{prtx}{idx:03d}.png', rgb_map)
            # rgb_map = np.concatenate((rgb_map, depth_map), axis=1)
            # imageio.imwrite(f'{savePath}/rgbd/{prtx}{idx:03d}.png', depth_map)
            np.savez(f'{savePath}/rgbd/{prtx}{idx:03d}.npz', depth=depth_map)

    imageio.mimwrite(f'{savePath}/{prtx}video.mp4', np.stack(rgb_maps), fps=24, quality=8)
    imageio.mimwrite(f'{savePath}/{prtx}depthvideo.mp4', np.stack(depth_maps), fps=24, quality=8)

    saveDirPath = resPath if resPath is not None else savePath
    if PSNRs:
        psnr = np.mean(np.asarray(PSNRs))
        if compute_extra_metrics:
            ssim = np.mean(np.asarray(ssims))
            # l_a = np.mean(np.asarray(l_alex))
            l_v = np.mean(np.asarray(l_vgg))
            np.savetxt(f'{saveDirPath}/{prtx}mean.txt', np.asarray([psnr, ssim, l_v]))
        else:
            np.savetxt(f'{saveDirPath}/{prtx}mean.txt', np.asarray([psnr]))
            
        np.savetxt(f'{saveDirPath}/test_views_PSNR.txt', np.asarray(PSNRs))
        np.savetxt(f'{saveDirPath}/test_views_ssim.txt', np.asarray(ssims))
        np.savetxt(f'{saveDirPath}/test_views_LPIPS_vgg.txt', np.asarray(l_vgg))

    return PSNRs

