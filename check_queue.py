import redis
import config

try:
    # Connect to Redis
    r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=0)
    # Check the connection
    r.ping()

    # Get the length of the default dramatiq queue
    queue_name = "dramatiq:default"
    queue_length = r.llen(queue_name)

    print(f"Length of queue '{queue_name}': {queue_length}")

except redis.exceptions.ConnectionError as e:
    print(f"Error connecting to Redis: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
