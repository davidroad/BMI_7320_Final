#!/usr/bin/env python3

import torch
from vega_model import VEGA
from utils import *
from learning_utils import *
import scanpy as sc
from scipy import sparse
from sklearn import preprocessing
import numpy as np
import itertools
import argparse



def train_vega(dev):
    """ Main """
    train_path = "./data/train_pbmc.h5ad"
    pathway_file = "./data/reactomes.gmt"
    LR = 1e-4
    N_EPOCHS=500
    p_drop = 0.5

    # Set model
    random_seed = 1
    # Out dir
    local_out = '/trained_models/kang_ctout_models/'
    torch.backends.cudnn.enabled = True
    torch.manual_seed(random_seed)
#     dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print('Using device:', dev, flush=True)
    dir_name = '.'+local_out
    # Read pathway file and data
    full_data = sc.read(train_path)
    for cell_type in full_data.obs['cell_type'].unique():
        print('Training model leaving out '+cell_type, flush=True)
        prefix_model = 'vega_kang_pbmc_%s_out_'%( cell_type)
        prefix_out = '10CV_vega_kang_pbmc_%s_out_res.npy'%(cell_type)
        train_data = full_data.copy()[~((full_data.obs['cell_type'] == cell_type) & (full_data.obs['condition'] == 'stimulated'))]
        labels = train_data.obs['cell_type']
        le = preprocessing.LabelEncoder()
        le.fit(labels)
        y = torch.Tensor(le.transform(labels))
        pathway_dict = read_gmt(pathway_file, min_g=0, max_g=1000)
        print(train_data.shape, flush=True)
        pathway_mask = create_pathway_mask(train_data.var.index.tolist(), pathway_dict, add_missing=1, fully_connected=True)
        if sparse.issparse(train_data.X):
            train_ds = train_data.X.A
        else:
            train_ds = train_data.X
        train_ds = torch.Tensor(train_ds)
        train_ds = UnsupervisedDataset(train_ds, targets=y)
        # Initialize CV
        kfold = KFoldTorch(cv=5, n_epochs=N_EPOCHS, lr=LR, train_p=10, test_p=10, num_workers=0, save_all=True, save_best=False, path_dir=dir_name, model_prefix=prefix_model)
        dict_params = {'pathway_mask':pathway_mask, 'beta':0.00005, 'dropout':p_drop, 'path_model':None, 'device':dev, 'positive_decoder':True}
        kfold.train_kfold(VEGA, dict_params, train_ds, batch_size=64)
        np.save(dir_name+prefix_out, kfold.cv_res_dict)
        print('Finished training for %s out'%(cell_type), flush=True)
    return

if __name__=="__main__":
    dev = torch.device("cuda:0") 
    train_vega(dev)
