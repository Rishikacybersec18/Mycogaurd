import math
import random
import shutil
import time
from pathlib import Path

import streamlit as st


# Local folders act as the distributed storage network.
BASE_DIR = Path(__file__).resolve().parent
NODE_NAMES = ["node1", "node2", "node3", "node4"]
NODE_PATHS = {name: BASE_DIR / name for name in NODE_NAMES}


def ensure_nodes() -> None:
    """Create the simulated node folders if they do not exist."""
    for path in NODE_PATHS.values():
        path.mkdir(parents=True, exist_ok=True)


def clear_nodes() -> None:
    """Remove every fragment from every node."""
    for path in NODE_PATHS.values():
        if not path.exists():
            continue
        for item in path.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


def initialize_state() -> None:
    """Prepare session state for the simulation."""
    defaults = {
        "file_name": None,
        "file_size": 0,
        "fragments": [],
        "storage_map": [],
        "upload_signature": None,
        "uploader_key": 0,
        "active_nodes": NODE_NAMES.copy(),
        "failed_nodes": [],
        "last_failed_node": None,
        "repair_log": [],
        "reconstructed_bytes": None,
        "network_ready": False,
        "self_destructed": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def fragment_bytes(file_bytes: bytes, parts: int) -> list[bytes]:
    """Split bytes into near-equal fragments."""
    chunk_size = max(1, math.ceil(len(file_bytes) / parts))
    return [
        file_bytes[index : index + chunk_size]
        for index in range(0, len(file_bytes), chunk_size)
    ]


def write_fragment_copy(node_name: str, fragment_index: int, copy_label: str, data: bytes) -> str:
    """Persist a fragment copy into a node folder."""
    path = NODE_PATHS[node_name] / f"fragment_{fragment_index + 1}_{copy_label}.bin"
    path.write_bytes(data)
    return str(path)


def ingest_file(uploaded_file) -> None:
    """Handle upload, fragmentation, and distributed storage."""
    ensure_nodes()
    clear_nodes()

    file_bytes = uploaded_file.getvalue()
    fragment_count = random.randint(3, 5)
    fragments = fragment_bytes(file_bytes, fragment_count)
    storage_map = []

    with st.status("Upload -> Fragment -> Store", expanded=True) as status:
        st.write(f"Loaded `{uploaded_file.name}` ({len(file_bytes)} bytes).")
        time.sleep(0.4)
        st.write("Fragmenting data...")
        time.sleep(0.7)

        for index, fragment in enumerate(fragments):
            primary, replica = random.sample(NODE_NAMES, 2)
            primary_path = write_fragment_copy(primary, index, "primary", fragment)
            replica_path = write_fragment_copy(replica, index, "replica", fragment)
            storage_map.append(
                {
                    "fragment_id": index + 1,
                    "size": len(fragment),
                    "primary_node": primary,
                    "replica_node": replica,
                    "primary_path": primary_path,
                    "replica_path": replica_path,
                }
            )
            st.write(
                f"Fragment {index + 1} stored in `{primary}` with mirrored backup in `{replica}`."
            )
            time.sleep(0.25)

        status.update(label="Mycelium storage network ready", state="complete")

    st.session_state.file_name = uploaded_file.name
    st.session_state.file_size = len(file_bytes)
    st.session_state.fragments = fragments
    st.session_state.storage_map = storage_map
    st.session_state.upload_signature = f"{uploaded_file.name}:{len(file_bytes)}"
    st.session_state.active_nodes = NODE_NAMES.copy()
    st.session_state.failed_nodes = []
    st.session_state.last_failed_node = None
    st.session_state.repair_log = []
    st.session_state.reconstructed_bytes = None
    st.session_state.network_ready = True
    st.session_state.self_destructed = False


def node_inventory(node_name: str) -> list[str]:
    """Return the fragment files currently present in a node."""
    path = NODE_PATHS[node_name]
    if not path.exists():
        return []
    return sorted(item.name for item in path.iterdir() if item.is_file())


def simulate_node_failure() -> None:
    """Delete one node's fragment files to simulate failure."""
    candidates = [node for node in st.session_state.active_nodes if node_inventory(node)]
    if not candidates:
        st.warning("No active node with fragments is available to fail.")
        return

    failed_node = random.choice(candidates)
    with st.status("Network monitor", expanded=True) as status:
        st.write(f"Failure detected in `{failed_node}`.")
        time.sleep(0.6)
        for file_name in node_inventory(failed_node):
            (NODE_PATHS[failed_node] / file_name).unlink()
        status.update(label=f"{failed_node} failed", state="error")

    st.session_state.active_nodes = [
        node for node in st.session_state.active_nodes if node != failed_node
    ]
    st.session_state.failed_nodes = sorted(
        set(st.session_state.failed_nodes + [failed_node])
    )
    st.session_state.last_failed_node = failed_node


def repair_network() -> None:
    """Recreate missing copies and reconstruct the original file."""
    if not st.session_state.network_ready:
        st.warning("Upload a file first so the repair workflow has data to protect.")
        return

    repair_log = []
    reconstructed_parts = []

    with st.status("DNA Repair Protocol", expanded=True) as status:
        st.write("Scanning nodes for missing fragments...")
        time.sleep(0.6)

        for item in st.session_state.storage_map:
            primary_exists = Path(item["primary_path"]).exists()
            replica_exists = Path(item["replica_path"]).exists()

            source_bytes = None
            if primary_exists:
                source_bytes = Path(item["primary_path"]).read_bytes()
            elif replica_exists:
                source_bytes = Path(item["replica_path"]).read_bytes()
            else:
                # The demo falls back to the original in-memory fragment so repair remains visible.
                source_bytes = st.session_state.fragments[item["fragment_id"] - 1]
                repair_log.append(
                    f"Fragment {item['fragment_id']} lost across the network; restored from protected memory."
                )

            reconstructed_parts.append(source_bytes)

            if not primary_exists and item["primary_node"] in st.session_state.active_nodes:
                write_fragment_copy(
                    item["primary_node"],
                    item["fragment_id"] - 1,
                    "primary",
                    source_bytes,
                )
                repair_log.append(
                    f"Fragment {item['fragment_id']} rebuilt in `{item['primary_node']}`."
                )

            if not replica_exists:
                target_node = item["replica_node"]
                if target_node not in st.session_state.active_nodes:
                    healthy_nodes = [
                        node
                        for node in NODE_NAMES
                        if node in st.session_state.active_nodes
                        and node != item["primary_node"]
                    ]
                    if healthy_nodes:
                        target_node = random.choice(healthy_nodes)
                        item["replica_node"] = target_node
                        item["replica_path"] = str(
                            NODE_PATHS[target_node]
                            / f"fragment_{item['fragment_id']}_replica.bin"
                        )

                if target_node in st.session_state.active_nodes:
                    write_fragment_copy(
                        target_node,
                        item["fragment_id"] - 1,
                        "replica",
                        source_bytes,
                    )
                    repair_log.append(
                        f"Fragment {item['fragment_id']} mirrored into `{target_node}`."
                    )

        st.write("Reconstructing lost data...")
        time.sleep(0.8)
        status.update(label="DNA repair complete", state="complete")

    st.session_state.repair_log = repair_log or ["No missing fragments detected."]
    st.session_state.reconstructed_bytes = b"".join(reconstructed_parts)


def activate_self_destruct() -> None:
    """Delete all fragments and reset the network state."""
    with st.status("Apoptosis protocol", expanded=True) as status:
        st.write("Activate Self Destruct received.")
        time.sleep(0.5)
        clear_nodes()
        st.write("All fragments removed from every node.")
        time.sleep(0.4)
        status.update(label="Self-destruct complete", state="complete")

    st.session_state.fragments = []
    st.session_state.storage_map = []
    st.session_state.upload_signature = None
    st.session_state.file_name = None
    st.session_state.file_size = 0
    st.session_state.uploader_key += 1
    st.session_state.active_nodes = NODE_NAMES.copy()
    st.session_state.failed_nodes = []
    st.session_state.last_failed_node = None
    st.session_state.repair_log = []
    st.session_state.reconstructed_bytes = None
    st.session_state.network_ready = False
    st.session_state.self_destructed = True


def render_step_flow() -> None:
    """Show the concept pipeline as a dashboard strip."""
    steps = ["Upload", "Fragment", "Store", "Monitor", "Repair", "Delete"]
    active = {
        "Upload": bool(st.session_state.file_name),
        "Fragment": bool(st.session_state.storage_map),
        "Store": bool(st.session_state.storage_map),
        "Monitor": st.session_state.network_ready,
        "Repair": bool(st.session_state.repair_log),
        "Delete": st.session_state.self_destructed,
    }

    cols = st.columns(len(steps))
    for col, step in zip(cols, steps):
        state = "ACTIVE" if active[step] else "WAITING"
        color = "#22c55e" if active[step] else "#64748b"
        col.markdown(
            f"""
            <div style="background:#0f172a;border-radius:14px;padding:12px 10px;border:1px solid #1e293b;text-align:center;">
                <div style="font-size:12px;color:{color};font-weight:700;letter-spacing:0.08em;">{state}</div>
                <div style="font-size:15px;color:#e2e8f0;font-weight:600;margin-top:4px;">{step}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_network() -> None:
    """Display a simple node map and node inventories."""
    st.subheader("Mycelium Network")
    cols = st.columns(4)

    for col, node_name in zip(cols, NODE_NAMES):
        files = node_inventory(node_name)
        is_active = node_name in st.session_state.active_nodes
        status = "ACTIVE" if is_active else "FAILED"
        background = "#052e16" if is_active else "#450a0a"
        border = "#22c55e" if is_active else "#ef4444"
        fragment_lines = "<br>".join(files) if files else "No fragments"

        col.markdown(
            f"""
            <div style="background:{background};border:1px solid {border};border-radius:16px;padding:16px;min-height:180px;">
                <div style="font-size:18px;font-weight:700;color:#f8fafc;">{node_name}</div>
                <div style="font-size:12px;color:{border};font-weight:700;margin:6px 0 12px 0;">{status}</div>
                <div style="font-size:13px;color:#cbd5e1;line-height:1.5;">{fragment_lines}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div style="margin-top:12px;background:#111827;border-radius:14px;padding:12px 16px;border:1px solid #1f2937;">
            <span style="color:#e5e7eb;font-weight:600;">Network Topology:</span>
            <span style="color:#93c5fd;"> node1 </span>
            <span style="color:#64748b;">●──●</span>
            <span style="color:#93c5fd;"> node2 </span>
            <span style="color:#64748b;">●──●</span>
            <span style="color:#93c5fd;"> node3 </span>
            <span style="color:#64748b;">●──●</span>
            <span style="color:#93c5fd;"> node4 </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="MycoGuard", page_icon="🧬", layout="wide")
    ensure_nodes()
    initialize_state()

    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #020617 0%, #0f172a 45%, #111827 100%);
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("MycoGuard")
    st.caption(
        "Bio-inspired security simulation using mycelium-style distribution, DNA-repair recovery, and apoptosis self-destruct."
    )

    render_step_flow()
    st.divider()

    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        st.subheader("1. File Upload")
        uploaded_file = st.file_uploader(
            "Upload a file to distribute across the simulated network",
            key=f"uploader_{st.session_state.uploader_key}",
        )

        if uploaded_file is not None:
            current_signature = f"{uploaded_file.name}:{uploaded_file.size}"
            if st.session_state.upload_signature != current_signature:
                ingest_file(uploaded_file)

        if uploaded_file is None and st.session_state.upload_signature is not None:
            clear_nodes()
            st.session_state.upload_signature = None
            st.session_state.file_name = None
            st.session_state.file_size = 0
            st.session_state.fragments = []
            st.session_state.storage_map = []
            st.session_state.active_nodes = NODE_NAMES.copy()
            st.session_state.failed_nodes = []
            st.session_state.last_failed_node = None
            st.session_state.repair_log = []
            st.session_state.reconstructed_bytes = None
            st.session_state.network_ready = False
            st.session_state.self_destructed = False

        if st.session_state.file_name:
            metric_a, metric_b, metric_c = st.columns(3)
            metric_a.metric("File Name", st.session_state.file_name)
            metric_b.metric("File Size", f"{st.session_state.file_size} bytes")
            metric_c.metric("Fragments", len(st.session_state.storage_map))

        if st.session_state.storage_map:
            st.subheader("2. Fragment Distribution")
            st.dataframe(
                [
                    {
                        "Fragment": f"Fragment {item['fragment_id']}",
                        "Size (bytes)": item["size"],
                        "Primary Node": item["primary_node"],
                        "Replica Node": item["replica_node"],
                    }
                    for item in st.session_state.storage_map
                ],
                use_container_width=True,
                hide_index=True,
            )

        render_network()

    with right:
        st.subheader("3. System Controls")

        if st.button(
            "Simulate Node Failure",
            use_container_width=True,
            disabled=not st.session_state.network_ready,
        ):
            simulate_node_failure()

        if st.session_state.last_failed_node:
            st.error(f"Node failure detected: `{st.session_state.last_failed_node}`")

        if st.button(
            "Run DNA Repair",
            use_container_width=True,
            disabled=not st.session_state.network_ready,
        ):
            repair_network()

        if st.session_state.repair_log:
            st.success("Repair activity log")
            for line in st.session_state.repair_log:
                st.write(f"- {line}")

        if st.session_state.reconstructed_bytes is not None:
            st.info(
                f"Recovered file size: {len(st.session_state.reconstructed_bytes)} bytes."
            )
            st.download_button(
                "Download Reconstructed File",
                data=st.session_state.reconstructed_bytes,
                file_name=f"recovered_{st.session_state.file_name or 'file'}",
                use_container_width=True,
            )

        st.divider()

        if st.button(
            "Activate Self Destruct",
            type="primary",
            use_container_width=True,
        ):
            activate_self_destruct()

        if st.session_state.self_destructed:
            st.warning("All fragments deleted. The mycelium network is now empty.")

        st.subheader("4. Concept Mapping")
        st.markdown(
            """
            - **Mycelium model:** fragments are spread across multiple local nodes.
            - **DNA repair:** missing copies are detected and rebuilt from surviving data.
            - **Apoptosis:** the whole network can destroy itself on command.
            """
        )


if __name__ == "__main__":
    main()
