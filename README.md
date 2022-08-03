# rhv-vm-cleaner

A python script that monitors VMs on RHV, if the VM has been powered off for more than two weeks, the script deletes the VM.

The script makes sure to notify the owner of the VM via mail that the VM has been marked for removal.
