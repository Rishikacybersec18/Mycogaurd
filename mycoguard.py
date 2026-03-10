import streamlit as st
import os
import random
import time

st.title("MycoGuard Bio-Inspired Security System")

nodes = ["nodes/node1","nodes/node2","nodes/node3","nodes/node4"]

uploaded_file = st.file_uploader("Upload File")

if uploaded_file:

    data = uploaded_file.read()

    chunk_size = max(1, len(data)//4)

    chunks = [data[i:i+chunk_size] for i in range(0,len(data),chunk_size)]

    st.subheader("Fragmenting File")

    for i,chunk in enumerate(chunks):

        node = random.choice(nodes)

        with open(f"{node}/fragment{i}.bin","wb") as f:
            f.write(chunk)

        st.write(f"Fragment {i} stored in {node}")

    st.success("Distributed across Mycelium Network")

    # Node Failure Simulation

if st.button("Simulate Node Failure"):

    failed = random.choice(nodes)

    for file in os.listdir(failed):
        os.remove(f"{failed}/{file}")

    st.error(f"{failed} has failed!")

    st.write("Initiating DNA Repair Protocol...")

    #Self-Destruct Feature (Apoptosis)

    if st.button("Activate Self Destruct"):

        st.warning("Apoptosis protocol initiated")

        time.sleep(3)

    for node in nodes:
        for file in os.listdir(node):
            os.remove(f"{node}/{file}")

    st.success("All fragments destroyed")
