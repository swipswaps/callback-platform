# Use Ubuntu as base (has Asterisk in universe repo)
FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Asterisk and Python
RUN apt-get update && apt-get install -y \
    asterisk \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create AGI scripts directory
RUN mkdir -p /var/lib/asterisk/agi-bin && \
    chmod 755 /var/lib/asterisk/agi-bin

# Install Python AGI library
RUN pip3 install pyst2

# Copy configuration files
COPY asterisk/conf/modules.conf /etc/asterisk/modules.conf
COPY asterisk/conf/extensions.conf /etc/asterisk/extensions.conf
COPY asterisk/conf/sip.conf /etc/asterisk/sip.conf
COPY asterisk/conf/pjsip.conf /etc/asterisk/pjsip.conf
COPY asterisk/conf/manager.conf /etc/asterisk/manager.conf

# Copy AGI scripts
COPY asterisk/agi-bin/ /var/lib/asterisk/agi-bin/
RUN chmod +x /var/lib/asterisk/agi-bin/*.py

# Expose ports
# 5060: SIP
# 5038: AMI (Asterisk Manager Interface)
# 10000-10100: RTP (media)
EXPOSE 5060/udp 5038 10000-10100/udp

# Run Asterisk in foreground
CMD ["asterisk", "-f", "-vvv"]

