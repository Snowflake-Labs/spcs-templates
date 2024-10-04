import time

import torch.distributed as dist

if __name__ == "__main__":
    print('start train')
    dist.init_process_group('gloo')
    print(f'RANK: {dist.get_rank()}')
    time.sleep(10000)
