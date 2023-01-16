# IP Fabric Ansible Demo

## Installation

```
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
pip install -r requirements.txt
```

## Playbooks

- [pb.1.snapshot_info.yml](pb.1.snapshot_info.yml)
  - Using the `snapshot_info` module
- [pb.2.snapshot_module.yml](pb.2.snapshot_module.yml)
  - Using the `snapshot` module
- [pb.3.table.yml](pb.3.table.yml)
  - Using the `table_info` module
- [pb.4.fix-ntp.yml](pb.4.fix-ntp.yml)
  - Putting everything together


