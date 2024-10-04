import os
import random

import torch
import torch.distributed as dist
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data.dataloader import DataLoader
from torch.utils.data.distributed import DistributedSampler
import wandb
import click


def _setup_wandb():
    WANDB_SECRET = os.environ.get('WANDB_SECRET')
    wandb.login(key=WANDB_SECRET)

    service_name = os.environ.get('SNOWFLAKE_SERVICE_NAME', 'test')
    wandb.init(project=f"experiment-{service_name}")


def _set_rnd_seeds(random_seed=0):
    torch.manual_seed(random_seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    random.seed(random_seed)


def _get_device(local_rank: int):
    if torch.cuda.is_available():
        return local_rank
    else:
        return None


def evaluate(model, device, test_loader):
    model.eval()

    correct = 0
    total = 0
    with torch.no_grad():
        for data in test_loader:
            images, labels = data[0].to(device), data[1].to(device)
            outputs = model(images)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    accuracy = correct / total

    return accuracy


def train(use_wandb: bool):
    rank = int(os.environ.get('RANK', 0))
    world_size = int(os.environ.get('WORLD_SIZE', 1))
    master_addr = os.environ.get('MASTER_ADDR', '0.0.0.0')
    master_port = int(os.environ.get('MASTER_PORT', 29501))
    local_rank = int(os.environ.get('LOCAL_RANK', 0))

    os.environ['MASTER_ADDR'] = master_addr
    os.environ['MASTER_PORT'] = str(master_port)
    os.environ['RANK'] = str(rank)
    os.environ['LOCAL_RANK'] = str(local_rank)
    os.environ['WORLD_SIZE'] = str(world_size)

    num_epoch = 100
    batch_size = 256
    lr = 0.01
    rnd_seed = 0
    epoch_metrics_iteration = 100
    train_test_iteration = 10
    _set_rnd_seeds(rnd_seed)

    print(f"Rank {rank}/{world_size} starting...")
    dist.init_process_group(backend="nccl" if torch.cuda.is_available() else "gloo",
                            init_method=f"tcp://{master_addr}:{master_port}",
                            world_size=world_size, rank=rank)

    transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])

    trainset = torchvision.datasets.CIFAR10(root='/tmp/cifar10/data', train=True, download=False,
                                            transform=transform)
    test_set = torchvision.datasets.CIFAR10(root="/tmp/cifar10/data", train=False, download=False,
                                            transform=transform)

    train_sampler = DistributedSampler(trainset, num_replicas=world_size, rank=rank)

    trainloader = DataLoader(trainset, batch_size=batch_size, shuffle=False, num_workers=2, sampler=train_sampler)
    testloader = DataLoader(dataset=test_set, batch_size=128, shuffle=False, num_workers=8)

    model = getattr(torchvision.models, 'resnet18')(pretrained=False).to(_get_device(local_rank))
    model = DDP(model, device_ids=[local_rank] if torch.cuda.is_available() else None)

    criterion = nn.CrossEntropyLoss().to(_get_device(local_rank))
    optimizer = optim.SGD(model.parameters(), lr=lr, momentum=0.9)

    print("Start training loop")
    for epoch in range(num_epoch):
        model.train()
        train_sampler.set_epoch(epoch)
        epoch_running_loss, epoch_loss = 0.0, 0.0

        if epoch % train_test_iteration == 0:
            if local_rank == 0:
                model.eval()
                accuracy = evaluate(model=model, device=_get_device(local_rank), test_loader=testloader)
                print(f"rank={rank} epoch={epoch}, testset accuracy={accuracy}")

        model.train()

        for batch_idx, data in enumerate(trainloader, 0):
            inputs, labels = data
            inputs, labels = inputs.to(_get_device(local_rank)), labels.to(_get_device(local_rank))
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            epoch_running_loss += loss.item()
            epoch_loss += loss.item()
            if batch_idx % epoch_metrics_iteration == 0:
                if use_wandb:
                    wandb.log({
                        "running_loss": epoch_running_loss / epoch_metrics_iteration,
                        "loss": epoch_loss,
                        "epoch": epoch
                    })
                print(
                    f'rank={rank} epoch={epoch} batch_index={batch_idx}, running_loss: {epoch_running_loss / epoch_metrics_iteration}, loss: {epoch_loss}')
                epoch_running_loss = 0.0

    dist.destroy_process_group()


@click.command()
@click.option('--use_wandb', is_flag=True, help="Wandb Secret")
def main(use_wandb: bool):
    if use_wandb:
        _setup_wandb()
    train(use_wandb)


if __name__ == "__main__":
    main()
