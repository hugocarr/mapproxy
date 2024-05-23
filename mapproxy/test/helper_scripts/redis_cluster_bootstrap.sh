#!/bin/bash
set -eoux pipefail

source config.sh

# Create temporary directories for Redis instances
REDIS_DIR=$(mktemp -d)
mkdir -p $REDIS_DIR/$REDIS_NODE_1_PORT $REDIS_DIR/$REDIS_NODE_2_PORT $REDIS_DIR/$REDIS_NODE_3_PORT

# Create redis.conf for 7000
cat <<EOF > $REDIS_DIR/$REDIS_NODE_1_PORT/redis.conf
port $REDIS_NODE_1_PORT
cluster-enabled yes
cluster-config-file nodes-$REDIS_NODE_1_PORT.conf
cluster-node-timeout 5000
appendonly yes
dir $REDIS_DIR/$REDIS_NODE_1_PORT
EOF

# Create redis.conf for 7001
cat <<EOF > $REDIS_DIR/$REDIS_NODE_2_PORT/redis.conf
port $REDIS_NODE_2_PORT
cluster-enabled yes
cluster-config-file nodes-$REDIS_NODE_2_PORT.conf
cluster-node-timeout 5000
appendonly yes
dir $REDIS_DIR/$REDIS_NODE_2_PORT
EOF

# Create redis.conf for 7002
cat <<EOF > $REDIS_DIR/$REDIS_NODE_3_PORT/redis.conf
port $REDIS_NODE_3_PORT
cluster-enabled yes
cluster-config-file nodes-$REDIS_NODE_3_PORT.conf
cluster-node-timeout 5000
appendonly yes
dir $REDIS_DIR/$REDIS_NODE_3_PORT
EOF

# Start Redis instances
redis-server $REDIS_DIR/$REDIS_NODE_1_PORT/redis.conf &
redis-server $REDIS_DIR/$REDIS_NODE_2_PORT/redis.conf &
redis-server $REDIS_DIR/$REDIS_NODE_3_PORT/redis.conf &

# Wait a few seconds to ensure all instances are up
sleep 5

# Create the Redis cluster
echo "yes" | redis-cli --cluster create 127.0.0.1:$REDIS_NODE_1_PORT 127.0.0.1:$REDIS_NODE_2_PORT 127.0.0.1:$REDIS_NODE_3_PORT --cluster-replicas 0

# Verify the cluster
redis-cli -p $REDIS_NODE_1_PORT cluster nodes

# Clean up the temporary directories after the script finishes
trap "rm -rf $REDIS_DIR" EXIT

echo "Redis cluster setup completed using temporary directories."
