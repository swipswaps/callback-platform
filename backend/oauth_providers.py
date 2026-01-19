"""
OAuth Provider Integration Module

Handles OAuth authentication flows for:
- Google
- Facebook
- Instagram
- X.com (Twitter)
- WhatsApp (via Meta Business API)

Security: All tokens are validated server-side only.
Privacy: Minimal scopes requested (name, email, phone where available).
"""

import requests
import logging
import os

# Configure logging per Rule 25
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(console_handler)
    
    file_handler = logging.FileHandler("/tmp/oauth_providers.log", mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(file_handler)


def get_user_info(provider, access_token):
    """
    Fetch user information from OAuth provider.
    
    Args:
        provider (str): Provider name (google, facebook, instagram, x, whatsapp)
        access_token (str): OAuth access token
        
    Returns:
        dict: User information with keys: name, email, phone (if available)
    """
    logger.info(f"Fetching user info from provider: {provider}")
    
    try:
        if provider == "google":
            return _get_google_user_info(access_token)
        elif provider == "facebook":
            return _get_facebook_user_info(access_token)
        elif provider == "instagram":
            return _get_instagram_user_info(access_token)
        elif provider == "x":
            return _get_x_user_info(access_token)
        elif provider == "whatsapp":
            return _get_whatsapp_user_info(access_token)
        else:
            logger.error(f"Unknown provider: {provider}")
            return {}
    except Exception as e:
        logger.error(f"Failed to fetch user info from {provider}: {str(e)}")
        return {}


def _get_google_user_info(token):
    """Fetch user info from Google OAuth API."""
    logger.debug("Requesting Google user info")
    
    response = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15
    )
    
    if response.status_code != 200:
        logger.error(f"Google API error: {response.status_code} - {response.text}")
        return {}
    
    data = response.json()
    logger.info(f"Google user info retrieved: {data.get('email', 'no-email')}")
    
    return {
        "name": data.get("name"),
        "email": data.get("email"),
        "phone": None  # Google OAuth doesn't provide phone by default
    }


def _get_facebook_user_info(token):
    """Fetch user info from Facebook Graph API."""
    logger.debug("Requesting Facebook user info")
    
    response = requests.get(
        "https://graph.facebook.com/me",
        params={
            "fields": "name,email",
            "access_token": token
        },
        timeout=15
    )
    
    if response.status_code != 200:
        logger.error(f"Facebook API error: {response.status_code} - {response.text}")
        return {}
    
    data = response.json()
    logger.info(f"Facebook user info retrieved: {data.get('email', 'no-email')}")
    
    return {
        "name": data.get("name"),
        "email": data.get("email"),
        "phone": None  # Facebook doesn't expose phone via basic OAuth
    }


def _get_instagram_user_info(token):
    """Fetch user info from Instagram Basic Display API."""
    logger.debug("Requesting Instagram user info")
    
    response = requests.get(
        "https://graph.instagram.com/me",
        params={
            "fields": "username",
            "access_token": token
        },
        timeout=15
    )
    
    if response.status_code != 200:
        logger.error(f"Instagram API error: {response.status_code} - {response.text}")
        return {}
    
    data = response.json()
    logger.info(f"Instagram user info retrieved: {data.get('username', 'unknown')}")
    
    return {
        "name": data.get("username"),
        "email": None,  # Instagram doesn't provide email
        "phone": None
    }


def _get_x_user_info(token):
    """Fetch user info from X.com (Twitter) API v2."""
    logger.debug("Requesting X.com user info")
    
    response = requests.get(
        "https://api.twitter.com/2/users/me",
        headers={"Authorization": f"Bearer {token}"},
        params={"user.fields": "name,username"},
        timeout=15
    )
    
    if response.status_code != 200:
        logger.error(f"X.com API error: {response.status_code} - {response.text}")
        return {}
    
    data = response.json().get("data", {})
    logger.info(f"X.com user info retrieved: {data.get('username', 'unknown')}")
    
    return {
        "name": data.get("name"),
        "email": None,  # X.com doesn't provide email via OAuth2
        "phone": None
    }


def _get_whatsapp_user_info(token):
    """
    Fetch user info from WhatsApp Business API.
    Note: Requires Meta Business verification and specific permissions.
    """
    logger.debug("Requesting WhatsApp user info")
    
    # WhatsApp Business API requires business verification
    # This is a placeholder - actual implementation requires Meta Business setup
    logger.warning("WhatsApp OAuth not fully implemented - requires Meta Business verification")
    
    return {
        "name": "WhatsApp User",
        "email": None,
        "phone": None  # Would be available with proper Meta Business setup
    }

