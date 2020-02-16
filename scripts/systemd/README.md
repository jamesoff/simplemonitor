This is a simple systemd service for `simplemonitor`

# Installation

Replace `/root/simplemonitor` with the location of your `simplemonitor` installation (two instances in the file)

Start the service

```
systemctl start simplemonitor.service
systemctl status simplemonitor.service
```

If everything looks good, enable a startup upon reboot

```
systemctl enable simplemonitor.service
```
