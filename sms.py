# sms.py
# Sends the OTP to the user's phone number.
#
# IMPORTANT (read this):
# Actually delivering an SMS needs a paid SMS gateway account (Fast2SMS,
# Twilio, MSG91, etc.) with an API key - a Flask app by itself cannot send
# text messages to a phone.
#
# This file uses Fast2SMS (popular for Indian numbers, has a free-credit
# trial): https://www.fast2sms.com
#
# TO GO LIVE:
#   1. Create a free account at fast2sms.com and verify your own number.
#   2. Copy your API key from the Fast2SMS dashboard.
#   3. Set it as an environment variable before running the app:
#        Windows (PowerShell):  $env:FAST2SMS_API_KEY="your_key_here"
#        Mac/Linux:             export FAST2SMS_API_KEY="your_key_here"
#   4. Restart the app (py app.py). OTPs will now be sent as real SMS.
#
# UNTIL you set that key, the app runs in DEV MODE: the OTP is printed
# in this terminal window instead of being texted, so you can still test
# the full forgot-password flow for free.

import os
import requests

FAST2SMS_API_KEY = os.environ.get("FAST2SMS_API_KEY")


def send_otp_sms(phone, otp):
    """Sends the OTP to `phone`. Falls back to printing it in the
    terminal if no SMS gateway API key is configured."""

    if not FAST2SMS_API_KEY:
        print("=" * 50)
        print(f"[DEV MODE] No SMS gateway configured.")
        print(f"[DEV MODE] OTP for {phone} is: {otp}")
        print("=" * 50)
        return True

    try:
        url = "https://www.fast2sms.com/dev/bulkV2"
        payload = {
            "route": "otp",
            "variables_values": otp,
            "numbers": phone,
        }
        headers = {"authorization": FAST2SMS_API_KEY}
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return True
    except Exception as exc:
        # SMS failed to send (bad key, no internet, etc.) - fall back to
        # printing so the user isn't completely locked out during testing.
        print(f"[SMS SEND FAILED] {exc}")
        print(f"[FALLBACK] OTP for {phone} is: {otp}")
        return False
