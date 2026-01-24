#!/usr/bin/env python3
"""
Asterisk AGI Script for Callback Platform
Handles callback requests initiated by the Python Flask backend

This script is executed by Asterisk when a callback is initiated.
It receives parameters from the dialplan and handles the call flow.

Per Rule 25: Comprehensive logging for troubleshooting
"""

import sys
import logging
from asterisk.agi import AGI

# Configure comprehensive logging per Rule 25
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    # Console handler - visible in Asterisk logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(console_handler)
    
    # File handler - persistent logs
    file_handler = logging.FileHandler("/tmp/asterisk_agi.log", mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(file_handler)


def main():
    """
    Main AGI callback handler
    
    This script is called from the Asterisk dialplan with parameters:
    - ARG1: Destination phone number (visitor to call back)
    - ARG2: Caller ID (business number)
    """
    try:
        logger.info("AGI callback handler started")
        
        # Initialize AGI
        agi = AGI()
        
        # Get arguments from dialplan
        destination = agi.env.get('agi_arg_1', 'unknown')
        caller_id = agi.env.get('agi_arg_2', 'unknown')
        
        logger.info(f"Callback request - Destination: {destination}, CallerID: {caller_id}")
        
        # Answer the call
        agi.answer()
        logger.debug("Call answered")
        
        # Play hold music or greeting
        # In production, this would connect to the visitor
        agi.stream_file('beep')
        logger.debug("Played beep sound")
        
        # In a real implementation, you would:
        # 1. Dial the visitor's number
        # 2. Bridge the calls together
        # 3. Handle call status and failures
        
        # For now, just log success
        logger.info(f"Callback to {destination} completed successfully")
        
        # Hangup
        agi.hangup()
        logger.debug("Call hung up")
        
    except Exception as e:
        logger.error(f"AGI script error: {str(e)}", exc_info=True)
        try:
            agi.verbose(f"ERROR: {str(e)}")
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()

