import netifaces
import torch.distributed.run as torch_runner
import os
import time
import socket

num_nodes = int(os.environ.get('NUM_NODES', '1'))
SERVICE_NAME = os.environ.get('SNOWFLAKE_SERVICE_NAME', 'test').lower()
SERVICE_INSTANCES_DNS = f"instances.{SERVICE_NAME}.dadm.svc.spcs.internal"
NUM_INSTANCES = num_nodes
QUERY_INTERVAL = 1
timeout_sec = 600


def query_service(service_name):
    try:
        ip_addresses = socket.gethostbyname_ex(service_name)[2]
        unique_ips = set(ip_addresses)
        return unique_ips
    except Exception as e:
        print(f"Failed to resolve {service_name}: {e}")
        return set()


def write_ips_to_file(ip_set, filename):
    sorted_ips = sorted(ip_set)
    with open(filename, 'w') as file:
        for ip in sorted_ips:
            file.write(f"{ip}\n")
    print(f"IP {sorted_ips} addresses written to {filename} in sorted order.")


def get_ip_for_interface(interface_name):
    try:
        addresses = netifaces.ifaddresses(interface_name)
        ipv4_info = addresses.get(netifaces.AF_INET)
        if ipv4_info:
            return ipv4_info[0]['addr']
        else:
            raise ValueError(f"No IPv4 address assigned to interface {interface_name}")
    except ValueError as e:
        raise ValueError(f"Error getting IP for interface {interface_name}: {e}")


def gather_hosts():
    if num_nodes == 1:
        return sorted([get_ip_for_interface('eth0')])
    print(f"Querying {SERVICE_INSTANCES_DNS} until we receive {NUM_INSTANCES} unique IP addresses...")
    start_time = time.time()
    while start_time + timeout_sec > time.time():
        ip_set = query_service(SERVICE_INSTANCES_DNS)
        if len(ip_set) == NUM_INSTANCES:
            print(f"Received {NUM_INSTANCES} unique IP addresses: {ip_set}")
            sorted_ips = sorted(ip_set)
            return sorted_ips

        time.sleep(QUERY_INTERVAL)

    ip_set = query_service(SERVICE_INSTANCES_DNS)
    raise ValueError(f"Discovered only len: {len(ip_set)}: {ip_set}, expected {NUM_INSTANCES} ip addresses")


def get_sorted_hosts():
    hosts = []
    with open('hosts.txt', 'r') as file:
        for line in file:
            hosts.append(line.strip())
    return hosts


def get_node_rank(hosts):
    my_ip_addr = get_ip_for_interface('eth0')
    for idx in range(len(hosts)):
        if hosts[idx] == my_ip_addr:
            return idx
    raise ValueError(f"IP {my_ip_addr} not found in {hosts}")


def spcs_run(args=None):
    job_hosts = gather_hosts()
    args = torch_runner.parse_args(args)
    args.node_rank = get_node_rank(job_hosts)
    master_addr = job_hosts[0]
    args.master_addr = master_addr
    print(f'start spcs runner with MASTER_ADDR: {master_addr}, node rank: {args.node_rank}')
    torch_runner.run(args)


if __name__ == "__main__":
    spcs_run()
