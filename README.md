# AWS Resource Tagger

Script to tag AWS resources - designed to run in Lambda.

Now we support to tag these resources:

- EBS : Based on Instance's tags

Limitations:

- Only untagged resources will be enforced to the tags.

## Setup

### Customize AWS Config Query

> Not recommended, could change the behavior of script

```bash
export CONFIG_QUERY_INSTANCES="SELECT resourceId, configuration.imageId, configuration.blockDeviceMappings, tags WHERE resourceType = 'AWS::EC2::Instance' AND configuration.state.name = 'running' OR configuration.state.name = 'stopped'"

```

### Filters

#### Map tags

List of Tag map sepparated by comma.

Syntax:

```bash
FILTER_TAGS_MAP="Name>role"
```

Map tags when desired tag is not present.

It's common used when defined to inheritance Instance tags but mandatory tags is not present, you can map tags to for existing desired tags.

Eg.: cenario01

```bash
InstanceA tags = "{Name: InstanceA, team: backend}"
FILTER_TAGS_INSTANCE="role,team,Name"
FILTER_TAGS_MAP="Name>role"
```

`InstanceA` has no tag `role`, but it will be created with the value of `Name`


#### VPC tags

List of VPCs ID sepparated by comma.

> TODO

Syntax:

```bash
FILTER_TAGS_VPC_ID="vpc-1234,vpc-4321"
FILTER_TAGS_VPC_KEY="team,env"
```

Filter to allow an top level inheritance to use default queries for the resource.

#### Instance tags

When using EBS module, the tags applyed to the volumes will be the same of instances. To filter tag keys, just give a list sepparated by commad:

```bash
export TAG_FILTER_KEYS_INSTANCE="role,product,team,Name"
```

> NOTE: the Instance block device mapping will be appended to tag Name

* Required Instance tags

```bash
export TAG_REQUIRED_KEYS_INSTANCE=Name,team,env,role
```

* Force default tags

```bash
export TAG_DEFAULT_COPY_KEY=Name
export TAG_DEFAULT_COPY_SPLIT=-,2
```

Syntax:

- `TAG_DEFAULT_COPY_KEY=<tag_name>`: Base Tag key to create default tag value (inheritance from)
- `TAG_DEFAULT_COPY_SPLIT=<separator>,<number_of_elements_to_join`: rules to filter the default values.

Eg.
Supposing that there is an cluster with instances with `tag:Name` variations by zone, as: `cluster1-frontend-use1-a, cluster1-frontend-use1-b`

The default env vars could be:

- `TAG_REQUIRED_KEYS_INSTANCE=Name,role`
- `TAG_DEFAULT_COPY_KEY=Name`
- `TAG_DEFAULT_COPY_SPLIT=-,2`

if no `tag:role` was found, the default value will be `cluster1-frontend` (two first elements joined by separator `-`)

## Usage

### Setup

Create IAM Execution role with permissions to:

- Make queries on AWS Config
- Put metrics to CloudWatch
- Describe EC2 resources

```bash
make setup-iam-role
```

Create the function:

```bash
make create-function
```

Create CloudWatch Scheduler Rule and associate with the function:

```bash
create-scheduled-rule
create-function-scheduler
create-scheduler-target
```

### Debug

* To run the code locally:

```bash
time make run
```

* DeBUG

```bash
LOG_LEVEL=DEBUG python3 ./main.py
```

* To get the ARN of Function

```bash
make echo-function-arn
```

* To get the ARN of IAM role used by Function

```bash
make echo-iam-role-arn
```

* To get the ARN of Cloudwatch Event Rule:

```bash
make echo-caller-rule
```

### Deploy

- To update a function

```bash
make update-function
```

## Contribute

There is a few list of TODOs to improve the code. See a few:

- support to tag EC2 instances that has no tag
- support to tag another resources, like EIP, Snapshots, AMIs, etc

To see more, just filter to string mark `TODO:` on the code.

Feel free to contribute.
