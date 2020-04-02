import copy
import json
from pprint import pprint

from aws import AWS
import utils



class Resources(object):
    def __init__(self):
        self.instances = {}
        self.volumes = {}
        self.snapshots = {}
        self.filtered_tag_keys = {}
        self.metric_prefix = 'resource_tagger_'
        self.metrics = {}
        self.aws = AWS()

        self.setup()
    
    def setup(self):
        self.instances.clear()
        self.volumes.clear()
        self.snapshots.clear()

        # Filters
        fk = os.getenv("TAG_FILTER_KEYS" or [])
        if isinstance(fk, list):
            self.filtered_tag_keys = fk
        elif isinstance(fk, str):
            self.filtered_tag_keys =fk.split(',')
        else:
            self.filtered_tag_keys = []
        
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


    def load_info_volumes(self):
        """Load all valumes that has not tags """

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

    def apply_tags_images(self):
        "TODO: what tags to use? Globals?"
        return
