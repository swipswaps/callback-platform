# Asterisk + Python AGI Implementation

## Overview

This document describes the Asterisk + Python AGI implementation as an alternative callback provider for the callback platform.

**Implementation Date**: 2026-01-20  
**Status**: ✅ COMPLETE - Asterisk container running, provider abstraction implemented

---

## Architecture

### Provider Abstraction Layer

The callback platform now supports multiple providers through an abstraction layer:

```
CallbackProvider (base class)
├── TwilioProvider (existing functionality preserved)
└── AsteriskProvider (new - AMI-based call origination)
```

### Components

1. **Docker Container** (`asterisk/`)
   - Ubuntu 22.04 base image
   - Asterisk PBX 18.10.0
   - Python 3 + pyst2 library
   - AMI (Asterisk Manager Interface) enabled

2. **Configuration Files** (`asterisk/conf/`)
   - `modules.conf` - Module loading configuration
   - `extensions.conf` - Dialplan for callback context
   - `sip.conf` - SIP configuration (for future SIP trunk integration)
   - `manager.conf` - AMI user credentials

3. **AGI Script** (`asterisk/agi-bin/callback_handler.py`)
   - Python AGI script for handling callback flow
   - Comprehensive logging per Rule 25

4. **Backend Integration** (`backend/app.py`)
   - `CallbackProvider` base class
   - `TwilioProvider` class (wraps existing Twilio functionality)
   - `AsteriskProvider` class (AMI-based call origination)
   - Provider selection via `CALLBACK_PROVIDER` environment variable

---

## Configuration

### Environment Variables

Add to `.env` file:

```bash
# Provider Selection (twilio or asterisk)
CALLBACK_PROVIDER=twilio  # Default: twilio

# Asterisk Configuration (for asterisk provider)
ASTERISK_HOST=asterisk
ASTERISK_AMI_PORT=5038
ASTERISK_AMI_USER=callback_manager
ASTERISK_AMI_SECRET=callback_secret_2026
```

### Docker Compose

The `docker-compose.yml` includes:
- `asterisk` service (ports 5060/UDP, 5038, 10000-10100/UDP)
- `backend` service (depends on asterisk)
- `callback-network` for service communication

---

## Usage

### Start Services

```bash
# Start Asterisk only
docker compose up -d asterisk

# Start all services
docker compose up -d
```

### Switch Providers

**Use Twilio (default)**:
```bash
export CALLBACK_PROVIDER=twilio
docker compose up -d backend
```

**Use Asterisk**:
```bash
export CALLBACK_PROVIDER=asterisk
docker compose up -d backend
```

### Verify Asterisk Status

```bash
# Check container status
docker ps | grep asterisk

# View Asterisk logs
docker logs callback-asterisk

# Check AMI connectivity
docker exec callback-asterisk asterisk -rx "manager show connected"
```

---

## Features Preserved (Rule 18)

✅ All existing Twilio functionality  
✅ OAuth social login  
✅ SQLite persistent storage  
✅ Real-time status tracking  
✅ SMS fallback for missed calls (Twilio only)  
✅ Comprehensive logging per Rule 25  
✅ Security: CORS, rate limiting, input validation  
✅ Business hours checking  
✅ Phone number validation (E.164 format)  
✅ Setup wizard integration  

---

## Provider Comparison

| Feature | TwilioProvider | AsteriskProvider |
|---------|----------------|------------------|
| Call Origination | ✅ Yes | ✅ Yes (via AMI) |
| SMS Support | ✅ Yes | ❌ No |
| Cost | $$ Paid service | Free (self-hosted) |
| Setup Complexity | Low (API keys) | Medium (Docker + config) |
| SIP Trunk Required | No | Yes (for production) |
| Business Hours SMS | ✅ Yes | ❌ No |

---

## Files Created

1. `asterisk/Dockerfile` - Asterisk container definition
2. `asterisk/conf/modules.conf` - Module configuration
3. `asterisk/conf/extensions.conf` - Dialplan
4. `asterisk/conf/sip.conf` - SIP configuration
5. `asterisk/conf/manager.conf` - AMI configuration
6. `asterisk/agi-bin/callback_handler.py` - AGI callback script

## Files Modified

1. `docker-compose.yml` - Added asterisk service
2. `backend/requirements.txt` - Added pyst2==0.5.1
3. `backend/app.py` - Added provider abstraction layer (+356 lines)

---

## Next Steps (Production Deployment)

1. **SIP Trunk Integration**
   - Configure SIP trunk in `asterisk/conf/sip.conf`
   - Update dialplan to use SIP trunk for outbound calls
   - Test call origination with real phone numbers

2. **Security Hardening**
   - Change AMI password in `manager.conf`
   - Restrict AMI access by IP
   - Enable TLS for AMI connections

3. **Monitoring**
   - Set up Asterisk logging to persistent volume
   - Monitor AMI connection health
   - Alert on call failures

4. **Testing**
   - Test callback flow end-to-end
   - Verify phone number validation
   - Test error handling and fallbacks

---

## Troubleshooting

### Asterisk Container Won't Start

```bash
# Check logs
docker logs callback-asterisk

# Common issues:
# - Missing configuration files
# - Port conflicts (5060, 5038)
# - Permission issues with AGI scripts
```

### AMI Connection Fails

```bash
# Verify AMI is listening
docker exec callback-asterisk netstat -tlnp | grep 5038

# Test AMI connection from backend
docker exec callback-backend python3 -c "
import socket
sock = socket.socket()
sock.connect(('asterisk', 5038))
print(sock.recv(1024))
sock.close()
"
```

### Provider Not Switching

```bash
# Check environment variable
docker exec callback-backend env | grep CALLBACK_PROVIDER

# Check backend logs
docker logs callback-backend | grep "provider"
```

---

## References

- [Asterisk Documentation](https://docs.asterisk.org/)
- [pyst2 Library](https://pypi.org/project/pyst2/)
- [Asterisk Manager Interface (AMI)](https://docs.asterisk.org/Configuration/Interfaces/Asterisk-Manager-Interface-AMI/)
- [Asterisk Gateway Interface (AGI)](https://docs.asterisk.org/Configuration/Interfaces/Asterisk-Gateway-Interface-AGI/)

