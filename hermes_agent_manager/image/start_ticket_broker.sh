#!/command/with-contenv sh
# Start the FM bridge ticket broker on the container network.
nohup s6-setuidgid hermes python3 /opt/ham/ticket_broker.py \
  >/var/log/ham-ticket-broker.log 2>&1 &
