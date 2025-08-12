import asyncio
from tasks import process_file
import os

print("Creating a dummy file for testing...")
dummy_file_path = "test_file.txt"
with open(dummy_file_path, "w") as f:
    f.write("This is the content of the test file.")
print(f"Dummy file created at: {os.path.abspath(dummy_file_path)}")

print("\nSending a test job to the queue...")
# We need to provide some dummy IDs that the bot would normally get from Telegram.
chat_id = 12345
message_id = 67890
local_path = os.path.abspath(dummy_file_path)

# Send the job to the dramatiq broker
process_file.send(chat_id, message_id, local_path=local_path)

print("\nTest job sent successfully!")
print("The worker should pick this up and process it in the background.")
print("Check worker.log for output.")
