import math
import random
import shutil
import time
from datetime import datetime
from pathlib import Path

import streamlit as st


# Local folders simulate distributed storage units behind the dashboard.
BASE_DIR = Path(__file__).resolve().parent
NODE_IDS = ["node1", "node2", "node3", "node4"]
NODE_PATHS = {node_id: BASE_DIR / node_id for node_id in NODE_IDS}


def ensure_nodes() -> None:
    """Create the local folders used by the simulation."""
    for path in NODE_PATHS.values():
        path.mkdir(parents=True, exist_ok=True)


def clear_nodes() -> None:
    """Remove all fragment files from every simulated storage unit."""
    for path in NODE_PATHS.values():
        if not path.exists():
            continue
        for item in path.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


def initialize_state() -> None:
    """Prepare Streamlit session state for the simulation dashboard."""
    defaults = {
        "file_name": None,
        "file_size": 0,
        "fragments": [],
        "fragment_map": [],
        "active_nodes": NODE_IDS.copy(),
        "failed_nodes": [],
        "last_failed_node": None,
        "reconstructed_bytes": None,
        "network_ready": False,
        "self_destructed": False,
        "logs": [],
        "upload_signature": None,
        "uploader_key": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def add_log(message: str, level: str = "info") -> None:
    """Append a time-stamped event to the live system log."""
    icons = {
        "info": "🔹",
        "success": "✅",
        "warning": "⚠️",
        "error": "🛑",
    }
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.insert(0, f"[{timestamp}] {icons.get(level, '🔹')} {message}")
    st.session_state.logs = st.session_state.logs[:20]


def fragment_bytes(file_bytes: bytes, part_count: int) -> list[bytes]:
    """Split the uploaded file into 3-5 near-equal fragments."""
    chunk_size = max(1, math.ceil(len(file_bytes) / part_count))
    return [
        file_bytes[index : index + chunk_size]
        for index in range(0, len(file_bytes), chunk_size)
    ]


def write_fragment(node_id: str, fragment_index: int, copy_kind: str, data: bytes) -> str:
    """Write one fragment copy into a simulated secure storage unit."""
    path = NODE_PATHS[node_id] / f"fragment_{fragment_index + 1}_{copy_kind}.bin"
    path.write_bytes(data)
    return str(path)


def get_node_files(node_id: str) -> list[str]:
    """Return all fragment files currently stored in a node."""
    path = NODE_PATHS[node_id]
    if not path.exists():
        return []
    return sorted(item.name for item in path.iterdir() if item.is_file())


def get_node_fragment_count(node_id: str) -> int:
    """Count how many fragment copies are stored in a node."""
    return len(get_node_files(node_id))


def reset_simulation(clear_storage: bool = True) -> None:
    """Reset the dashboard state."""
    if clear_storage:
        clear_nodes()
    st.session_state.file_name = None
    st.session_state.file_size = 0
    st.session_state.fragments = []
    st.session_state.fragment_map = []
    st.session_state.active_nodes = NODE_IDS.copy()
    st.session_state.failed_nodes = []
    st.session_state.last_failed_node = None
    st.session_state.reconstructed_bytes = None
    st.session_state.network_ready = False
    st.session_state.self_destructed = False
    st.session_state.upload_signature = None
    st.session_state.uploader_key += 1
    add_log("Simulation reset. Secure storage units cleared.", "warning")


def ingest_file(uploaded_file) -> None:
    """Handle upload, fragmentation, and distributed storage."""
    ensure_nodes()
    clear_nodes()

    file_bytes = uploaded_file.getvalue()
    fragment_count = random.randint(3, 5)
    fragments = fragment_bytes(file_bytes, fragment_count)
    fragment_map = []

    add_log(f"File uploaded successfully: {uploaded_file.name} ({len(file_bytes)} bytes).", "success")

    with st.status("🔒 Initializing secure ingestion pipeline", expanded=True) as status:
        st.write("Fragmenting data...")
        add_log("Fragmenting data into secure fragments.", "info")
        time.sleep(0.6)

        for index, fragment in enumerate(fragments):
            primary_node, backup_node = random.sample(NODE_IDS, 2)
            primary_path = write_fragment(primary_node, index, "primary", fragment)
            backup_path = write_fragment(backup_node, index, "backup", fragment)
            fragment_record = {
                "fragment_id": index + 1,
                "size": len(fragment),
                "primary_node": primary_node,
                "backup_node": backup_node,
                "primary_path": primary_path,
                "backup_path": backup_path,
            }
            fragment_map.append(fragment_record)
            st.write(
                f"Fragment {index + 1} routed to {primary_node} with redundant backup in {backup_node}."
            )
            add_log(
                f"Fragment {index + 1} stored in {primary_node}; backup copy stored in {backup_node}.",
                "info",
            )
            time.sleep(0.2)

        st.write("Distributing fragments to secure nodes...")
        add_log("Distributing fragments to secure storage units.", "success")
        time.sleep(0.5)
        status.update(label="🟢 Secure distribution complete", state="complete")

    st.session_state.file_name = uploaded_file.name
    st.session_state.file_size = len(file_bytes)
    st.session_state.fragments = fragments
    st.session_state.fragment_map = fragment_map
    st.session_state.active_nodes = NODE_IDS.copy()
    st.session_state.failed_nodes = []
    st.session_state.last_failed_node = None
    st.session_state.reconstructed_bytes = None
    st.session_state.network_ready = True
    st.session_state.self_destructed = False
    st.session_state.upload_signature = f"{uploaded_file.name}:{uploaded_file.size}"


def simulate_node_failure() -> None:
    """Simulate failure by wiping one active node."""
    candidates = [node_id for node_id in st.session_state.active_nodes if get_node_files(node_id)]
    if not candidates:
        st.warning("No active secure storage unit is currently holding fragments.")
        return

    failed_node = random.choice(candidates)
    with st.status("⚠️ Node failure simulation", expanded=True) as status:
        st.write(f"Node failure detected in {failed_node}.")
        add_log(f"Node failure detected in {failed_node} - initiating rerouting.", "error")
        time.sleep(0.7)
        for file_name in get_node_files(failed_node):
            (NODE_PATHS[failed_node] / file_name).unlink()
        st.write("Node marked offline.")
        time.sleep(0.4)
        status.update(label=f"🔴 {failed_node} failed", state="error")

    st.session_state.active_nodes = [
        node_id for node_id in st.session_state.active_nodes if node_id != failed_node
    ]
    st.session_state.failed_nodes = sorted(set(st.session_state.failed_nodes + [failed_node]))
    st.session_state.last_failed_node = failed_node


def run_self_healing() -> None:
    """Rebuild missing copies and reconstruct the file from redundancy."""
    if not st.session_state.network_ready:
        st.warning("Upload a file before running the repair simulation.")
        return

    repair_messages = []
    reconstructed_parts = []

    with st.status("🧬 DNA repair protocol", expanded=True) as status:
        st.write("Scanning secure nodes for missing fragments...")
        add_log("Scanning network for missing fragments.", "warning")
        time.sleep(0.6)

        for item in st.session_state.fragment_map:
            primary_exists = Path(item["primary_path"]).exists()
            backup_exists = Path(item["backup_path"]).exists()

            if primary_exists:
                source_bytes = Path(item["primary_path"]).read_bytes()
            elif backup_exists:
                source_bytes = Path(item["backup_path"]).read_bytes()
            else:
                source_bytes = st.session_state.fragments[item["fragment_id"] - 1]
                repair_messages.append(
                    f"Fragment {item['fragment_id']} recovered from protected redundancy memory."
                )
                add_log(
                    f"Fragment {item['fragment_id']} recovered from protected redundancy memory.",
                    "warning",
                )

            reconstructed_parts.append(source_bytes)

            if not primary_exists and item["primary_node"] in st.session_state.active_nodes:
                write_fragment(item["primary_node"], item["fragment_id"] - 1, "primary", source_bytes)
                repair_messages.append(
                    f"Fragment {item['fragment_id']} rebuilt in {item['primary_node']}."
                )

            if not backup_exists:
                target_node = item["backup_node"]
                if target_node not in st.session_state.active_nodes:
                    replacement_pool = [
                        node_id
                        for node_id in st.session_state.active_nodes
                        if node_id != item["primary_node"]
                    ]
                    if replacement_pool:
                        target_node = random.choice(replacement_pool)
                        item["backup_node"] = target_node
                        item["backup_path"] = str(
                            NODE_PATHS[target_node] / f"fragment_{item['fragment_id']}_backup.bin"
                        )

                if target_node in st.session_state.active_nodes:
                    write_fragment(target_node, item["fragment_id"] - 1, "backup", source_bytes)
                    repair_messages.append(
                        f"Fragment {item['fragment_id']} mirrored to {target_node}."
                    )

        st.write("Reconstructing missing fragments using redundancy...")
        add_log("Reconstructing missing fragments using redundancy.", "success")
        time.sleep(0.8)
        status.update(label="🟢 Self-healing complete", state="complete")

    st.session_state.reconstructed_bytes = b"".join(reconstructed_parts)
    for message in repair_messages[:8]:
        add_log(message, "info")

    if not repair_messages:
        add_log("No fragment loss detected. Redundancy check passed.", "success")


def activate_self_destruct() -> None:
    """Run the apoptosis simulation with a visible countdown."""
    with st.status("💥 Apoptosis protocol", expanded=True) as status:
        for number in [3, 2, 1]:
            st.write(f"Secure deletion in {number}...")
            add_log(f"Self-destruct countdown: {number}", "warning")
            time.sleep(0.7)
        clear_nodes()
        st.write("All fragments securely deleted.")
        add_log("All fragments securely deleted.", "error")
        time.sleep(0.4)
        status.update(label="🔴 Self-destruct complete", state="complete")

    st.session_state.fragments = []
    st.session_state.fragment_map = []
    st.session_state.reconstructed_bytes = None
    st.session_state.network_ready = False
    st.session_state.self_destructed = True
    st.session_state.active_nodes = NODE_IDS.copy()
    st.session_state.failed_nodes = []
    st.session_state.last_failed_node = None
    st.session_state.file_name = None
    st.session_state.file_size = 0
    st.session_state.upload_signature = None
    st.session_state.uploader_key += 1


def render_styles() -> None:
    """Inject dashboard styling for the simulation."""
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(34,197,94,0.16), transparent 28%),
                radial-gradient(circle at top right, rgba(59,130,246,0.16), transparent 24%),
                linear-gradient(180deg, #030712 0%, #0b1120 60%, #111827 100%);
            color: #e5e7eb;
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1320px;
        }
        .dashboard-card {
            background: rgba(15, 23, 42, 0.86);
            border: 1px solid rgba(71, 85, 105, 0.55);
            border-radius: 18px;
            padding: 18px;
            box-shadow: 0 18px 30px rgba(2, 6, 23, 0.28);
        }
        .hero-card {
            background: linear-gradient(135deg, rgba(17,24,39,0.95), rgba(15,23,42,0.95));
            border: 1px solid rgba(34,197,94,0.35);
            border-radius: 22px;
            padding: 24px;
            box-shadow: 0 18px 40px rgba(0,0,0,0.28);
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin-top: 14px;
        }
        .summary-item {
            background: rgba(2, 6, 23, 0.65);
            border: 1px solid rgba(51, 65, 85, 0.8);
            border-radius: 16px;
            padding: 14px;
        }
        .summary-label {
            color: #93a3b8;
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .summary-value {
            color: #f8fafc;
            font-size: 18px;
            font-weight: 700;
            margin-top: 6px;
            word-break: break-word;
        }
        .section-title {
            color: #f8fafc;
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
        }
        .log-panel {
            background: rgba(2, 6, 23, 0.9);
            border: 1px solid rgba(51, 65, 85, 0.8);
            border-radius: 16px;
            padding: 14px;
            min-height: 320px;
            max-height: 420px;
            overflow-y: auto;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            color: #d1fae5;
            white-space: pre-wrap;
        }
        .route-row {
            background: rgba(2, 6, 23, 0.55);
            border: 1px solid rgba(51, 65, 85, 0.7);
            border-radius: 14px;
            padding: 12px 14px;
            margin-bottom: 10px;
        }
        .node-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
            margin-top: 14px;
        }
        .node-card {
            border-radius: 20px;
            padding: 20px;
            min-height: 170px;
            position: relative;
            overflow: hidden;
        }
        .node-card.active {
            background: linear-gradient(180deg, rgba(6,95,70,0.55), rgba(6,78,59,0.24));
            border: 1px solid rgba(34,197,94,0.65);
        }
        .node-card.failed {
            background: linear-gradient(180deg, rgba(127,29,29,0.58), rgba(69,10,10,0.3));
            border: 1px solid rgba(248,113,113,0.75);
        }
        .node-orb {
            width: 62px;
            height: 62px;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 14px;
        }
        .node-card.active .node-orb {
            background: rgba(34,197,94,0.18);
            border: 2px solid rgba(34,197,94,0.85);
            color: #bbf7d0;
        }
        .node-card.failed .node-orb {
            background: rgba(248,113,113,0.16);
            border: 2px solid rgba(248,113,113,0.85);
            color: #fecaca;
        }
        .node-title {
            color: #f8fafc;
            font-size: 1.05rem;
            font-weight: 700;
        }
        .node-status {
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-top: 4px;
        }
        .node-meta {
            color: #dbeafe;
            font-size: 14px;
            margin-top: 14px;
            line-height: 1.7;
        }
        .network-link {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            color: #60a5fa;
            margin: 12px 0 2px 0;
            font-size: 13px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    """Render the top banner and summary cards."""
    status_text = "Protected" if st.session_state.network_ready else "Idle"
    file_label = st.session_state.file_name or "No file uploaded"
    size_label = f"{st.session_state.file_size} bytes" if st.session_state.file_size else "0 bytes"
    fragment_label = str(len(st.session_state.fragment_map))
    active_label = str(len(st.session_state.active_nodes))

    st.markdown(
        f"""
        <div class="hero-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:13px;letter-spacing:0.12em;text-transform:uppercase;color:#86efac;font-weight:700;">
                        🌐 Bio-Inspired Secure Data Simulation
                    </div>
                    <div style="font-size:2rem;font-weight:800;color:#f8fafc;margin-top:8px;">
                        MycoGuard Bio-Inspired Security System
                    </div>
                    <div style="color:#94a3b8;margin-top:8px;max-width:720px;">
                        Distributed storage inspired by mycelium networks, self-healing recovery modeled after DNA repair, and secure deletion modeled after apoptosis.
                    </div>
                </div>
                <div style="padding:10px 14px;border-radius:999px;background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);color:#bbf7d0;font-weight:700;">
                    🔒 System Status: {status_text}
                </div>
            </div>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-label">Protected File</div>
                    <div class="summary-value">{file_label}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">File Size</div>
                    <div class="summary-value">{size_label}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Fragments</div>
                    <div class="summary-value">{fragment_label}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Active Nodes</div>
                    <div class="summary-value">{active_label} / 4</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_upload_center() -> None:
    """Render a centered upload section at the top of the page."""
    left_space, center, right_space = st.columns([1, 1.8, 1])
    with center:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📤 Secure Data Ingestion</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload a file to distribute across secure storage units",
            key=f"uploader_{st.session_state.uploader_key}",
        )

        if uploaded_file is not None:
            current_signature = f"{uploaded_file.name}:{uploaded_file.size}"
            if st.session_state.upload_signature != current_signature:
                ingest_file(uploaded_file)

        if st.session_state.file_name:
            st.success("File uploaded successfully")
            st.write(f"**File:** `{st.session_state.file_name}`")
            st.write(f"**Size:** `{st.session_state.file_size} bytes`")
            st.write("**Status:** Secure ingestion complete")
        else:
            st.caption("Upload a file to start fragmentation, node distribution, and monitoring.")
        st.markdown("</div>", unsafe_allow_html=True)


def render_controls_panel() -> None:
    """Render the left-side control panel."""
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🎛️ Simulation Controls</div>', unsafe_allow_html=True)
    st.caption("Control the distributed storage network and trigger security events.")

    if st.button("⚠️ Simulate Node Failure", use_container_width=True, disabled=not st.session_state.network_ready):
        simulate_node_failure()

    if st.button("🧬 Run Self-Healing", use_container_width=True, disabled=not st.session_state.network_ready):
        run_self_healing()

    if st.button("💥 Activate Self Destruct", use_container_width=True, disabled=not st.session_state.network_ready):
        activate_self_destruct()

    if st.button("♻️ Reset Simulation", use_container_width=True):
        reset_simulation()

    st.markdown("---")
    st.markdown("**Current State**")
    if st.session_state.last_failed_node:
        st.error(f"Node failure detected - `{st.session_state.last_failed_node}` is offline.")
    elif st.session_state.network_ready:
        st.success("All secure storage units are currently operational.")
    else:
        st.info("Waiting for file upload.")

    if st.session_state.self_destructed:
        st.warning("All fragments have been securely deleted.")

    st.markdown("---")
    st.markdown("**Bio-Inspired Concepts**")
    st.write("🌐 Mycelium model: data is spread across distributed secure nodes.")
    st.write("🧬 DNA repair: redundancy is used to reconstruct missing fragments.")
    st.write("💥 Apoptosis: the system can securely self-delete all stored fragments.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_fragment_routes() -> None:
    """Render the fragment routing view."""
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🧩 Fragment Routing</div>', unsafe_allow_html=True)
    if not st.session_state.fragment_map:
        st.caption("Fragment distribution details will appear here after upload.")
    else:
        for item in st.session_state.fragment_map:
            st.markdown(
                f"""
                <div class="route-row">
                    <div style="font-weight:700;color:#f8fafc;">Fragment {item['fragment_id']}</div>
                    <div style="color:#93c5fd;margin-top:6px;">
                        Size: {item['size']} bytes
                    </div>
                    <div style="color:#cbd5e1;margin-top:4px;">
                        Primary storage: <strong>{item['primary_node']}</strong> &nbsp;|&nbsp; Backup storage: <strong>{item['backup_node']}</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


def render_network_panel() -> None:
    """Render the visual network as secure storage units."""
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔒 Secure Storage Network</div>', unsafe_allow_html=True)
    st.caption("Nodes represent secure distributed storage units, not folders.")

    st.markdown(
        """
        <div class="network-link">
            <span>node1</span>
            <span>●────●</span>
            <span>node2</span>
            <span>●────●</span>
            <span>node3</span>
            <span>●────●</span>
            <span>node4</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    first_row = st.columns(2, gap="medium")
    second_row = st.columns(2, gap="medium")
    node_columns = first_row + second_row

    for col, node_id in zip(node_columns, NODE_IDS):
        active = node_id in st.session_state.active_nodes
        status_text = "Active" if active else "Failed"
        status_color = "#86efac" if active else "#fca5a5"
        fragment_count = get_node_fragment_count(node_id)
        with col:
            st.markdown(
                f"""
                <div class="node-card {'active' if active else 'failed'}">
                    <div class="node-orb">🔒</div>
                    <div class="node-title">{node_id.upper()}</div>
                    <div class="node-status" style="color:{status_color};">{status_text}</div>
                    <div class="node-meta">
                        <div>Secure storage unit ID: <b>{node_id}</b></div>
                        <div>Stored fragment copies: <b>{fragment_count}</b></div>
                        <div>Redundancy mode: <b>{'Online' if active else 'Offline'}</b></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


def render_logs_panel() -> None:
    """Render the live system event log."""
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📜 System Log</div>', unsafe_allow_html=True)
    if not st.session_state.logs:
        log_text = "[system] Awaiting secure ingestion event..."
    else:
        log_text = "\n".join(st.session_state.logs)
    st.markdown(f'<div class="log-panel">{log_text}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_recovery_panel() -> None:
    """Render recovery summary and reconstructed file download."""
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🧬 Recovery Console</div>', unsafe_allow_html=True)
    if st.session_state.reconstructed_bytes is None:
        st.caption("Run self-healing to reconstruct missing fragments and recover the protected file.")
    else:
        st.success("Reconstruction complete. Missing fragments recovered using redundancy.")
        st.write(f"Recovered file size: `{len(st.session_state.reconstructed_bytes)} bytes`")
        st.download_button(
            "⬇️ Download Reconstructed File",
            data=st.session_state.reconstructed_bytes,
            file_name=f"recovered_{st.session_state.file_name or 'mycoguard_file'}",
            use_container_width=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="MycoGuard Bio-Inspired Security System",
        page_icon="🔒",
        layout="wide",
    )
    ensure_nodes()
    initialize_state()
    render_styles()

    st.markdown(
        """
        <style>
        div[data-testid="stFileUploader"] section {
            border: 1px dashed rgba(34,197,94,0.55);
            border-radius: 16px;
            background: rgba(2,6,23,0.42);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_header()
    st.markdown("")
    render_upload_center()
    st.markdown("")

    left_panel, main_panel = st.columns([0.32, 0.68], gap="large")

    with left_panel:
        render_controls_panel()

    with main_panel:
        top_row_left, top_row_right = st.columns([0.58, 0.42], gap="large")
        with top_row_left:
            render_network_panel()
        with top_row_right:
            render_logs_panel()

        st.markdown("")
        bottom_row_left, bottom_row_right = st.columns([0.55, 0.45], gap="large")
        with bottom_row_left:
            render_fragment_routes()
        with bottom_row_right:
            render_recovery_panel()


if __name__ == "__main__":
    main()
