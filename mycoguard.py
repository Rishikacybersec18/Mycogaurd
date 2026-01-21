import shutil
import os
import time

# ---------------- READ DATA ---------------- #
with open("/Users/rishu_06/Desktop/basic projects/biology/message.txt", "r") as f:
    data = f.read()

print("Original Data:")
print(data)

# ---------------- SPLIT DATA ---------------- #
chunks = [
    data[:len(data)//3],
    data[len(data)//3: 2*len(data)//3],
    data[2*len(data)//3:]
]

nodes = ["node1", "node2", "node3"]

for i in range(3):
    with open(f"{nodes[i]}/chunk{i+1}.txt", "w") as f:
        f.write(chunks[i])

# ---------------- SHOW FILE SIZES ---------------- #
for i in range(3):
    path = f"node{i+1}/chunk{i+1}.txt"
    print(path, "→ size:", os.path.getsize(path))

# ---------------- BACKUP SYSTEM ---------------- #
backup_map = {
    "chunk1.txt": ["node2"],
    "chunk2.txt": ["node3"],
    "chunk3.txt": ["node1"]
}

for chunk, backups in backup_map.items():
    num = chunk.replace("chunk", "").replace(".txt", "")
    original_node = f"node{num}"

    for backup_node in backups:
        shutil.copy(
            f"{original_node}/{chunk}",
            f"{backup_node}/{chunk}"
        )

print("Backup copies created.")

# ---------------- FUNCTIONS ---------------- #
def list_files():
    files = set()
    for node in nodes:
        for f in os.listdir(node):
            files.add(f)
    return list(files)

def delete_file_everywhere(filename):
    for node in nodes:
        path = os.path.join(node, filename)
        if os.path.exists(path):
            os.remove(path)
    print(f"\n'{filename}' has been securely deleted from all nodes.")

def start_timer(filename):
    ttl = int(input("\nSet time (in seconds) after which data should self-destruct: "))
    print(f"\nTimer started for '{filename}' ({ttl} seconds)")
    time.sleep(ttl)

    print(f"\nTime expired for '{filename}'")
    permission = input("Do you want to delete this data? (yes/no): ").lower()

    if permission == "yes":
        delete_file_everywhere(filename)
    else:
        print("\nDeletion denied.")
        choice = input("Reset timer or set new timer? (reset/new): ").lower()

        if choice in ["reset", "new"]:
            start_timer(filename)
        else:
            print("Invalid choice. Data retained safely.")

# ---------------- MAIN PROGRAM ---------------- #
available_files = list_files()

if not available_files:
    print("No data available.")
else:
    print("\nAvailable data files:")
    for f in available_files:
        print("-", f)

    selected_file = input("\nEnter the filename you want to manage: ")

    if selected_file in available_files:
        start_timer(selected_file)
    else:
        print("File not found in MycoGuard system.")
