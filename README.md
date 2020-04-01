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

### Filter tags

When using EBS module, the tags applyed to the volumes will be the same of instances. To filter tag keys, just give a list sepparated by commad:

```bash
export TAG_FILTER_KEYS="role,product,team,Name"
```

> NOTE: the Instance block device mapping will be appended to tag Name

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
