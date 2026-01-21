import shutil
import os

with open("/Users/rishu_06/Desktop/basic projects/biology/message.txt", "r") as f:
 data = f.read()
 
print("Original Data:")
print(data)
chunks = [
    data[:len(data)//3],
    data[len(data)//3: 2*len(data)//3],
    data[2*len(data)//3:]
]

nodes=["node1","node2","node3"]
for i in range(3):
    with open(f"{nodes[i]}/chunk{i+1}.txt","w+") as f:
        f.write(chunks[i])
        f.flush()
f.close()   

for i in range(3):
    path = f"node{i+1}/chunk{i+1}.txt"
    print(path, "→ size:", os.path.getsize(path))

        


# Backup locations for each chunk
backup_map = {
    "chunk1.txt": ["node2"],
    "chunk2.txt": ["node3"],
    "chunk3.txt": ["node1"]
}

for chunk, backups in backup_map.items():
    # Extract number from 'chunk3.txt'
    num = chunk.replace("chunk", "").replace(".txt", "")
    original_node = f"node{num}"

    for backup_node in backups:
        shutil.copy(
            f"{original_node}/{chunk}",
            f"{backup_node}/{chunk}"
        )

print("Backup copies created.")
