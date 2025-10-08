#!/usr/bin/env python3
"""
WhatsApp notification script for Claude Code hooks.
Sends a WhatsApp message when a project run completes.
"""
import sys
import pywhatkit
from datetime import datetime

def send_whatsapp_message(phone_number, message):
    """
    Send a WhatsApp message instantly.

    Args:
        phone_number (str): WhatsApp number in format +1234567890
        message (str): Message to send
    """
    try:
        # sendwhatmsg_instantly opens WhatsApp Web and sends message
        # Requires WhatsApp Web to be logged in on default browser
        pywhatkit.sendwhatmsg_instantly(
            phone_no=phone_number,
            message=message,
            wait_time=20,  # Wait 20 seconds for WhatsApp Web to load
            tab_close=True,  # Close the tab after sending
            close_time=5  # Close after 5 seconds
        )
        print(f"✓ Message sent successfully to {phone_number}")
        return True
    except Exception as e:
        print(f"✗ Error sending WhatsApp message: {e}")
        # Try alternative method if instant fails
        import time
        import pyautogui
        try:
            print("Retrying with manual Enter press...")
            time.sleep(2)
            pyautogui.press('enter')
            print("✓ Message sent with manual trigger")
            return True
        except:
            return False

if __name__ == "__main__":
    # Default phone number (you need to update this)
    PHONE_NUMBER = "+5521997891800"  # Your WhatsApp number

    # Get custom message from command line or use default
    if len(sys.argv) > 1:
        custom_message = " ".join(sys.argv[1:])
    else:
        custom_message = "Project run completed!"

    # Add timestamp to message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"🤖 Claude Code: {custom_message}\n⏰ {timestamp}"

    # Send the message
    send_whatsapp_message(PHONE_NUMBER, message)
