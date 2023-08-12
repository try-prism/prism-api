# Setup

## Production

CloudWatch Agent, Dashboard, and Alarm JSON config files support the following variables:

> {instance_id}: Replaced with each EC2 instance ID in your Ray cluster.

> {region}: Replaced with your Ray cluster’s region.

> {cluster_name}: Replaced with your Ray cluster name.

### [Ray](https://docs.ray.io/en/latest/cluster/vms/user-guides/launching-clusters/aws.html)

1. cd to the ray directory

```bash
cd ray
```

2. Create or update the cluster. When the command finishes, it will print out the command that can be used to SSH into the cluster head node

```bash
ray up ray.yaml
```

3. Get a remote shell on the head node

```bash
ray attach ray.yaml
```

4. Try running a Ray program

```bash
python -c 'import ray; ray.init()'
exit
```

5. Tear down the cluster

```bash
ray down ray.yaml
```

## Local QA

### [Milvus Vector Store](https://milvus.io/docs/install_standalone-docker.md)

1. cd to the milvus directory

```bash
cd milvus
```

2. Start the docker container

```bash
docker-compose up -d
```

3. Check whether the container is running

```bash
docker-compose ps
```

You can also stop milvus container

```bash
docker-compose down
```
