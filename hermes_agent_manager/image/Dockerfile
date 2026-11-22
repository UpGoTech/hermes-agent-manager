FROM nousresearch/hermes-agent:latest

USER root

RUN apt-get -o Acquire::Retries=3 update \
 && DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
    bash-completion \
    file \
    iproute2 \
    jq \
    less \
    locales \
    nano \
    net-tools \
    psmisc \
    sudo \
    tree \
    unzip \
    vim \
    wget \
 && rm -rf /var/lib/apt/lists/* \
 && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
 && dpkg-reconfigure --frontend=noninteractive locales \
 && usermod -s /bin/bash hermes \
 && printf 'hermes ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/ham \
 && chmod 0440 /etc/sudoers.d/ham \
 && mkdir -p /etc/bash.bashrc.d /opt/ham /etc/cont-init.d

COPY bashrc /etc/bash.bashrc.d/ham.bashrc
COPY ticket_broker.py /opt/ham/ticket_broker.py
COPY start_ticket_broker.sh /etc/cont-init.d/99-ham-ticket-broker

RUN printf '\nif [ -f /etc/bash.bashrc.d/ham.bashrc ]; then\n  . /etc/bash.bashrc.d/ham.bashrc\nfi\n' >> /etc/bash.bashrc \
 && chmod 0755 /opt/ham/ticket_broker.py /etc/cont-init.d/99-ham-ticket-broker
