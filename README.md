# Attendance Machine

## Install Requirements
```
pip install -r requirements.txt
```
## Run
```
python /home/pi/dev/MVP/attendance-device-b1/server.py
```
then open [localhost:5000](http://localhost:5000) on your browser.

## Auto Run on Raspberry Pi Startup
1 - Open `/home/pi/.config/lxsession/LXDE-pi` and write `@lxterminal` at the bottom of the file.
2 - Open `/home/pi/.bashrc` and write `python /home/pi/dev/MVP/attendance-device-b1/server.py & chromium-browser --kiosk http://localhost:5000` right before the last line.
3 - Restart the Raspberry Pi and enjoy.
