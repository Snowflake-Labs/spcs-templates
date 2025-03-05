import click
import torchvision
import torchvision.transforms as transforms


@click.command()
def main():
    dest_dir = "./data"
    transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
    torchvision.datasets.CIFAR10(root=dest_dir, train=True, download=True, transform=transform)
    torchvision.datasets.CIFAR10(root=dest_dir, train=False, download=True, transform=transform)

if __name__ == "__main__":
    main()
