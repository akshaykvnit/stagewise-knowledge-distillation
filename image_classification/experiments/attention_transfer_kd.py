import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.functional")
from comet_ml import Experiment
from fastai.vision import *
import torch
import argparse
import os
from image_classification.arguments import get_args
from image_classification.datasets.dataset import get_dataset
from image_classification.utils.utils import *
from image_classification.models.custom_resnet import *
from trainer import *


args = get_args(description='Attention Transfer KD', mode='train')
expt = 'attention-kd'

torch.manual_seed(args.seed)
if args.gpu != 'cpu':
    args.gpu = int(args.gpu)
    torch.cuda.set_device(args.gpu)
    torch.cuda.manual_seed(args.seed)

hyper_params = {
    "dataset": args.dataset,
    "model": args.model,
    "stage": 0,
    "num_classes": 10,
    "batch_size": 64,
    "num_epochs": args.epoch,
    "learning_rate": 1e-4,
    "seed": args.seed,
    "percentage":args.percentage,
    "gpu": args.gpu,
}

data = get_dataset(dataset=hyper_params['dataset'],
                   batch_size=hyper_params['batch_size'],
                   percentage=args.percentage)

learn, net = get_model(hyper_params['model'], hyper_params['dataset'], data, teach=True)
learn.model, net = learn.model.to(args.gpu), net.to(args.gpu)

teacher = learn.model

sf_student, sf_teacher = get_features(net, teacher, experiment=expt)

if args.api_key:
    project_name = expt + '-' + hyper_params['model'] + '-' + hyper_params['dataset']
    experiment = Experiment(api_key=args.api_key, project_name=project_name, workspace=args.workspace)
    experiment.log_parameters(hyper_params)

optimizer = torch.optim.Adam(net.parameters(), lr=hyper_params["learning_rate"])
loss_function2 = nn.MSELoss()
loss_function = nn.CrossEntropyLoss()
savename = get_savename(hyper_params, experiment=expt)
best_val_acc = 0

for epoch in range(hyper_params['num_epochs']):
    student, train_loss, val_loss, val_acc, best_val_acc = train(
                                                                net,
                                                                teacher,
                                                                data,
                                                                sf_teacher,
                                                                sf_student,
                                                                loss_function,
                                                                loss_function2,
                                                                optimizer,
                                                                hyper_params,
                                                                epoch,
                                                                savename,
                                                                best_val_acc,
                                                                expt=expt
                                                                )
    if args.api_key:
        experiment.log_metric("train_loss", train_loss)
        experiment.log_metric("val_loss", val_loss)
        experiment.log_metric("val_acc", val_acc * 100)
