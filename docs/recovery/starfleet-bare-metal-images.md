# Starfleet Bare-Metal Image Plan

## Purpose

Create full-disk recovery images for Spot Core and every worker so a failed SSD or HDD can be restored with Clonezilla.

Images are stored on the NAS, not on Spot Core and not on the Starfleet tower.

## Imaging method

Boot each unit from Clonezilla USB and save a savedisk image directly to the NAS.

Do not image the live running OS from inside Linux unless it is an emergency-only copy.

## NAS target for Clonezilla

Use Clonezilla samba_server.

Server/IP: 192.168.50.10
NAS name: unimatrix6
SMB share: docker
Directory: /starfleet-images
Username: ogre

Clonezilla target path:

//192.168.50.10/docker/starfleet-images

## Clonezilla menu path

Clonezilla live
device-image
samba_server
Beginner mode
savedisk

Use savedisk, not saveparts.

## Image naming

Format:

YYYYMMDD-host-purpose-disk

Examples:

20260626-spot-core-boot-sda
20260626-spot-worker-05-boot-nvme0n1

## Known disks

| Unit | Disk to image | Size | Purpose |
|---|---:|---:|---|
| spot-core | /dev/sda | 238.5G | boot disk |
| spot-worker-01 | /dev/nvme0n1 | 1.8T | boot disk |
| spot-worker-02 | /dev/sda | 119.2G | boot disk |
| spot-worker-02 | /dev/sdb | 465.8G | optional NTFS/data disk |
| spot-worker-03 | /dev/sda | 476.9G | boot disk |
| spot-worker-04 | /dev/nvme0n1 | 465.8G | boot disk |
| spot-worker-04 | /dev/nvme1n1 | 465.8G | ai-data disk mounted at /mnt/ai-data |
| spot-worker-05 | /dev/nvme0n1 | 238.5G | boot disk |
| spot-worker-06 | unknown | unknown | wait until physical repair/RAM test |

Do not image loop devices, DVD drives, or card readers.

## Recommended order

Start with a smaller worker first to prove the NAS path works.

1. spot-worker-05 /dev/nvme0n1
2. spot-worker-03 /dev/sda
3. spot-worker-02 /dev/sda
4. spot-worker-01 /dev/nvme0n1
5. spot-worker-04 /dev/nvme0n1
6. spot-worker-04 /dev/nvme1n1
7. spot-core /dev/sda
8. spot-worker-06 after repair/RAM test
9. OPNsense config export plus full disk image

## W6 rule

Do not image W6 until it is stable.

Current W6 status:

Ping: OK
Ollama 11434: OK
SSH 22: opens but hangs/times out
Physical state: suspected freeze / possible RAM issue

Before imaging W6:

1. Hard power cycle.
2. Boot and test SSH.
3. If frozen again, reseat RAM.
4. Run Memtest86+ from USB.
5. Require at least 2 clean passes.
6. Then inventory disk.
7. Then image.

## After each image

Boot the unit normally and validate from Spot Core:

cd ~/spot-stack || exit 1
watch/project/spot-project-status.sh

Expected:

RESULT: PASS
FAIL=0

W6 may remain WARN until repaired.

## Restore process

1. Replace failed disk.
2. Boot Clonezilla USB.
3. Select device-image.
4. Select samba_server.
5. Connect to //192.168.50.10/docker/starfleet-images.
6. Select restoredisk.
7. Pick the matching image.
8. Restore to the replacement internal disk.
9. Reboot.
10. Run watch/project/spot-project-status.sh from Spot Core.

## Current recovery layers

Layer 1: GitHub repo
Layer 2: config/state backups
Layer 3: Clonezilla full-disk images
