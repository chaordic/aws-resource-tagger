import copy
import json
import os
from pprint import pprint

from aws import AWS
import utils



class Resources(object):
    def __init__(self):
        self.instances = {}
        self.volumes = {}
        self.snapshots = {}
        self.filtered_tag_keys = []
        self.require_tags_instance = []
        self.metric_prefix = 'resource_tagger_'
        self.metrics = {}
        self.aws = AWS()

        self.tag_default_copy_key = ''
        self.tag_default_copy_split = ['-', 2]

        self.setup()
    
    def setup(self):
        self.instances.clear()
        self.volumes.clear()
        self.snapshots.clear()

        # Filters
        fk = os.getenv("TAG_FILTER_KEYS_INSTANCE" or [])
        if isinstance(fk, list):
            self.filtered_tag_keys = fk
        elif isinstance(fk, str):
            self.filtered_tag_keys =fk.split(',')
        else:
            self.filtered_tag_keys = []
        
        # Require tags for Instance
        rt = os.getenv("TAG_REQUIRED_KEYS_INSTANCE" or [])
        if isinstance(rt, list):
            self.require_tags_instance = rt
        elif isinstance(rt, str):
            self.require_tags_instance =rt.split(',')
        else:
            self.require_tags_instance = []

        # Copy tag value when it's defined
        self.tag_default_copy_key = os.getenv("TAG_DEFAULT_COPY_KEY" or '')
        ts = os.getenv("TAG_DEFAULT_COPY_SPLIT" or '')
        if isinstance(ts, list):
            self.tag_default_copy_split = ts
        elif isinstance(ts, str):
            self.tag_default_copy_split =ts.split(',')
        else:
            self.tag_default_copy_split = []

        # Metrics
        self.metrics = {
            "total_instances": 0,
            "total_volumes": 0,
            "total_snapshots": 0,
        }


    def load_info_instances(self):
        for instance in self.aws.get_instances():
            try:
                i = self.instances[instance["resourceId"]]
            except KeyError:
                self.instances[instance["resourceId"]] = {}
                i = self.instances[instance["resourceId"]]
                i["volumes"] = {}
                i["volumes_ebs"] = {}
            i["tags"] = copy.deepcopy(utils.tag_list_to_dict(instance["tags"]))
            try:
                i["imageId"] = instance["configuration"]["imageId"]
            except:
                pass
            for b in instance["configuration"]["blockDeviceMappings"]:
                try:
                    i["volumes_ebs"][b["ebs"]["volumeId"]] = b["deviceName"]
                except KeyError:
                    i["volumes"][b["deviceName"]] = b

    def init_info_instances(self):
        """Init will load instances to dict only if the instances is empty """
        if len(self.instances) <= 0:
            self.load_info_instances()
        return

    def load_info_volumes(self):
        """Load all valumes that has not tags """

        self.init_info_instances()

        volumes = self.aws.get_volumes()
        for vol in volumes:
            if 'Tags' in volumes[vol]:
                # Ignor volumes that alread have tags.
                # TODO: enforce default tags when it's not present.
                continue

            v = copy.deepcopy(volumes[vol])
            if vol not in self.volumes:
                self.volumes[vol] = {}
            
            if v['SnapshotId'] != "":
                self.volumes[vol]["snapshoot"] = v['SnapshotId']
                try:
                    s = self.snapshots[v['SnapshotId']]
                except KeyError:
                    self.snapshots[v['SnapshotId']] = {}
                    s = self.snapshots[v['SnapshotId']]
                s["volume_id"] = vol
            
            if len(v["Attachments"]) > 0:
                for a in v["Attachments"]:
                    try:
                        cur_tags = self.tag_filter(self.instances[a['InstanceId']]["tags"])
                        # self.volumes[vol]["instance_tags"] = new_tags
                    except KeyError:
                        cur_tags = {
                            "error": "Instance tag's is NotFound."
                        }
                    self.volumes[vol]["instance_attached"] = a['InstanceId']
                    self.volumes[vol]["attached"] = "yes"
                    new_tags = copy.deepcopy(cur_tags)
                    try:
                        device = self.instances[a['InstanceId']]["volumes_ebs"][vol]
                    except KeyError:
                        device = ''
                    if 'Name' in new_tags:
                        new_tags["Name"] += " " + device
                    self.volumes[vol]["tags"] = new_tags
            else:
                self.volumes[vol]["attached"] = "no"

        return

    def show_report(self):
        if LOG_LEVEL == "DEBUG":
            print(">> EC2 Instances: ")
            pprint(self.instances)
            
            print(">> Snapshoots: ")
            pprint(self.snapshots)
            
            print(">> Untagged volumes: ")
            pprint(self.volumes)
        
        msg = ("Total untagged volumes: {}".format(len(self.volumes)))
        #logger.info(msg)
        print(msg)
        msg = ("Total snapshoots to tag: {}".format(len(self.snapshots)))
        #logger.info(msg)
        print(msg)

    def add_metrics(self):
        self.aws.add_metrics(
            data={
                "name": "total_untagged_resources",
                "value": len(self.volumes),
                "dimensions": {
                    "Name": "resource",
                    "Value": "volumes"
                }
            }
        )

    def tag_filter(self, tags):
        tags_filtered = {}
        tags_filtered.clear()
        for t in tags:
            if t in self.filtered_tag_keys:
                tags_filtered.update({t: tags[t]})
        return tags_filtered

    def apply_tags_volumes(self):

        self.load_info_volumes()

        messages = []
        if len(self.volumes) <= 0:
            return
        for vol in self.volumes.keys():
            volume = self.volumes[vol]

            try:
                if volume["attached"] != "yes":
                    messages.append("ignoring volume {}=unattached to instance".format(vol))
                    continue
            except KeyError:
                pass
            try:
                if len(volume["tags"]) <= 0:
                    messages.append("ignoring volume {}=empty tags".format(vol))
                    continue
                if 'error' in volume["tags"]:
                    messages.append("ignoring volume {}={}".format(vol, str(volume["tags"]) ))
                    continue
            except KeyError as e:
                messages.append("ignoring volume {}=KeyError {}".format(vol, e))
                continue

            msg = ("{}={}".format(vol, str(volume["tags"])))
            logging.info(msg)
            messages.append(msg)
            self.aws.clients["ec2"].create_tags(
                    Resources=[vol],
                    Tags=utils.tag_dict_to_list(volume["tags"]))
        print("Tags applied to volumes: {}".format(json.dumps(messages)))
        return

    def apply_tags_snapshots(self):
        "TODO: use same tags of Volumes"
        return

    def apply_tags_instances(self):
        """ TODO:
        - use global/default tags.
        - Overwrite existing?
        - Useful to enforce to whole account; but in shared Account?
        - how to distinguish between two resources?
        """
        return

    def apply_tags_instance(self, instance_id, tags):
        self.aws.clients["ec2"].create_tags(
            Resources=[instance_id],
            Tags=tags)


    def apply_tags_images(self):
        "TODO: what tags to use? Globals?"
        return

    def apply_tags_from_event(self, event):
        if 'instance-id' in event["detail"]:
            return self.process_event_instance(event)

        elif 'event' in event["detail"]:
            if event["detail"]["event"] == "createVolume":
                return self.process_event(event)

        return {
                "error": "event not found",
                "event": event
            }

    def process_event_instance(self, event):

        instance_id = event["detail"]["instance-id"]
        instance = self.aws.get_instance_tags_api(instance_id)

        if not instance:
            print("ERR - No Tags or resource found for ID: {}".format(instance_id))
            return

        instance_tags = utils.tag_list_to_dict(instance["Tags"])

        missing_keys = self.check_required_tags(instance_tags)
        if len(missing_keys) <= 0:
            print("That's OK, all required Tags was defined to resource_id: {}".format(instance_id))
            return

        try:
            vpc_id = instance["VpcId"]
        except:
            vpc_id = ''

        vpc = self.aws.get_vpc_tags(vpc_id)
        if len(vpc) <= 0:
            print("ERR - No VPC [{}] found, skipping tagger".format(vpc_id))
            return

        try:
            vpc_tags = utils.tag_list_to_dict(vpc[0]["tags"])
        except KeyError:
            print("ERR - No VPC [{}] tags found, skipping tagger".format(vpc_id))
            return
        except:
            raise

        # discovery and fill tags to apply based on required (missing)
        tags_to_apply = self.mount_required_tags_instance(
            missing_keys=missing_keys,
            vpc_tags=vpc_tags,
            instance_tags=instance_tags
        )

        msg = {
            "msg": "Applying tags to Instance",
            "tags_to_apply": tags_to_apply,
            "resource_id": instance_id,
            "current_resource_tags": instance_tags,
            "current_vpc_tags": vpc_tags,
            "found_missing_keys": missing_keys
        }
        print(msg)
        return self.apply_tags_instance(
            instance_id=instance["InstanceId"],
            tags=utils.tag_dict_to_list(tags_to_apply)
        )

    def check_required_tags(self, instance_tags):
        missing_keys = []
        missing_keys.clear()
        for k in self.require_tags_instance:
            try:
                v = instance_tags[k]
            except KeyError:
                missing_keys.append(k)

        return missing_keys

    def mount_required_tags_instance(self, missing_keys, vpc_tags, instance_tags):
        """
        Check the missing keys and mount the tags to apply based on
        filters, VPC and Instance tags.
        """
        tags_to_apply = {}

        cnt = 0
        for k in missing_keys:
            try:
                tags_to_apply[k] = vpc_tags[k]
            except KeyError:
                try:
                    copy_tag = instance_tags[self.tag_default_copy_key]

                    tag_value = ''
                    cnt = 0
                    sep = self.tag_default_copy_split[0]
                    offset = int(self.tag_default_copy_split[1])
                    # print(sep, offset)
                    for v in copy_tag.split(sep):
                        # print(k, v)
                        tag_value += v
                        cnt += 1
                        if cnt >= offset:
                            break
                        tag_value += '-'

                    tags_to_apply[k] = tag_value
                except Exception as e:
                    print("Unexpected error: ", e)
                    raise

        return tags_to_apply
