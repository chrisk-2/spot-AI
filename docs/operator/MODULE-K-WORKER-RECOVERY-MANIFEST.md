# Module K — Worker Recovery Manifest Standard

## Purpose

Define the minimum recovery manifest required for any worker rebuild.

## Required Fields

- worker_name
- role
- hostname
- ip_address
- operating_system
- hardware_profile
- gpu_profile
- storage_layout
- mount_requirements
- required_models
- validation_commands
- recovery_source
- manifest_version

## Boundary

Manifest creation does not authorize recovery execution.
