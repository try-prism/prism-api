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

### [Milvus Cli](https://github.com/zilliztech/milvus_cli)

1. Download the latest release of milvus_cli-<version>-macOS

https://github.com/zilliztech/milvus_cli/releases/latest

2. Run the following

```bash
sudo chmod +x milvus_cli-<version>-macOS
```

3. Run milvus-cli

```bash
./milvus_cli-<version>-macOS
```

4. Try to connect to the local Milvus vector store

```bash
milvus_cli > connect
```

5. You can also list the collections

```bash
milvus_cli > list collections
+----+-------------------+
|    | Collection Name   |
+====+===================+
|  0 | llamalection      |
+----+-------------------+
```

6. See the description of the collections

```bash
milvus_cli > describe collection -c llamalection
+---------------+----------------------------------------------------------+
| Name          | llamalection                                             |
+---------------+----------------------------------------------------------+
| Description   |                                                          |
+---------------+----------------------------------------------------------+
| Is Empty      | False                                                    |
+---------------+----------------------------------------------------------+
| Entities      | 77                                                       |
+---------------+----------------------------------------------------------+
| Primary Field | id                                                       |
+---------------+----------------------------------------------------------+
| Schema        | Description:                                             |
|               |                                                          |
|               | Auto ID: False                                           |
|               |                                                          |
|               | Fields(* is the primary field):                          |
|               |  - *id VARCHAR  Unique ID                                |
|               |  - doc_id VARCHAR  Source document ID                    |
|               |  - text VARCHAR  The embedding vector                    |
|               |  - embedding FLOAT_VECTOR dim: 1536 The embedding vector |
|               |  - node VARCHAR  The node content                        |
+---------------+----------------------------------------------------------+
| Partitions    | - _default                                               |
+---------------+----------------------------------------------------------+
| Indexes       | - embedding                                              |
+---------------+----------------------------------------------------------+
```
