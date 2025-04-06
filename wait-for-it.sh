#!/usr/bin/env bash
# wait-for-it.sh -- wait until a service is ready

set -e

host_port="$1"  # Expected format: host:port
shift
cmd="$@"

# Split host and port using IFS (internal field separator)
IFS=":" read -r host port <<< "$host_port"

if [[ -z "$host" || -z "$port" ]]; then
  >&2 echo "Error: Invalid format for host:port ('$host_port'). Expected 'host:port'."
  exit 1
fi

>&2 echo "Waiting for $host:$port to become available..."

# Keep pinging the host and port using nc until successful
until nc -z "$host" "$port"; do
  >&2 echo "Service $host:$port is unavailable - sleeping"
  sleep 1
done

>&2 echo "Service $host:$port is up - executing command"
exec $cmd