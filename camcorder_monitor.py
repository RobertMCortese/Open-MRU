import ctypes
import subprocess
import time
import RPi.GPIO as GPIO
import signal
import sys
import os

# ----------------------
# Setup GPIO (pin 23)
# ----------------------
GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)
GPIO.output(23, GPIO.LOW)

# ----------------------
# FireWire / AV/C setup
# ----------------------
libavc = ctypes.cdll.LoadLibrary("libavc1394.so")

libavc.avc1394_open.restype = ctypes.c_int
handle = libavc.avc1394_open(0)   # first FireWire card
if handle < 0:
    raise RuntimeError("Could not open FireWire handle")

node = 1  # Adjust based on your camcorder node ID

def get_transport_state():
    """
    Query camcorder AV/C transport state.
    Returns operand byte or None if invalid.
    """
    cmd = (0x01 << 24) | (0x20 << 16) | (0x20 << 8) | 0x60  # STATUS, VTR, Transport, Record
    response = libavc.avc1394_transaction_block(handle, node, cmd, 4)
    if response < 0:
        return None
    return response & 0xFF  # operand

# ----------------------
# dvgrab management
# ----------------------
dvgrab_process = None

def start_dvgrab():
    global dvgrab_process
    if dvgrab_process is None:
        print("▶ Starting dvgrab...")
        dvgrab_process = subprocess.Popen(
            ["dvgrab", "--autosplit", "capture-"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

def stop_dvgrab():
    global dvgrab_process
    if dvgrab_process is not None:
        print("⏹ Stopping dvgrab...")
        dvgrab_process.terminate()
        dvgrab_process.wait()
        dvgrab_process = None

# ----------------------
# Graceful shutdown
# ----------------------
def cleanup(signalnum=None, frame=None):
    print("Cleaning up...")
    stop_dvgrab()
    GPIO.output(23, GPIO.LOW)
    GPIO.cleanup()
    libavc.avc1394_close(handle)
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

# ----------------------
# Main polling loop
# ----------------------
print("Monitoring camcorder transport state...")

try:
    while True:
        state = get_transport_state()
        if state == 0x60:  # RECORD FORWARD
            GPIO.output(23, GPIO.HIGH)
            start_dvgrab()
        else:
            GPIO.output(23, GPIO.LOW)
            stop_dvgrab()
        time.sleep(1)  # poll once per second
except KeyboardInterrupt:
    cleanup()
