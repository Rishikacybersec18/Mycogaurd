import math
import random
import shutil
import time
from datetime import datetime, time as dt_time
from pathlib import Path

import streamlit as st


# Local directories simulate secure storage units.
BASE_DIR = Path(__file__).resolve().parent
NODE_IDS = ["node1", "node2", "node3", "node4"]
NODE_PATHS = {node_id: BASE_DIR / node_id for node_id in NODE_IDS}
REDUNDANCY_COPIES = 2


def ensure_nodes() -> None:
    """Create local storage folders for the node simulation."""
    for path in NODE_PATHS.values():
        path.mkdir(parents=True, exist_ok=True)


def clear_node_files() -> None:
    """Delete all fragment files from all simulated nodes."""
    for path in NODE_PATHS.values():
        if not path.exists():
            continue
        for item in path.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


def build_default_nodes() -> dict:
    """Return the default node model."""
    return {
        node_id: {
            "label": node_id.upper(),
            "status": "Active",
            "fragments": [],
        }
        for node_id in NODE_IDS
    }


def init_state() -> None:
    """Initialize the app session state."""
    defaults = {
        "nodes": build_default_nodes(),
        "fragments": {},
        "file_name": None,
        "file_size": 0,
        "upload_signature": None,
        "uploader_key": 0,
        "reconstructed_bytes": None,
        "network_ready": False,
        "system_state": "Healthy",
        "logs": [],
        "status_text": None,
        "status_level": "info",
        "expiry_time": None,
        "show_schedule_popup": False,
        "show_expiry_popup": False,
        "self_destructed": False,
        "selected_expiry_date": datetime.now().date(),
        "selected_expiry_time": dt_time(hour=18, minute=0),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def add_log(message: str, level: str = "info") -> None:
    """Append one message to the chronological system log."""
    icon_map = {
        "success": "✅",
        "error": "🛑",
        "info": "🔹",
        "warning": "⚠️",
    }
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {icon_map.get(level, '🔹')} {message}")
    st.session_state.logs = st.session_state.logs[-50:]


def set_status(message: str, level: str) -> None:
    """Set the single action feedback message shown below controls."""
    st.session_state.status_text = message
    st.session_state.status_level = level


def node_fragment_path(node_id: str, fragment_id: int) -> Path:
    """Build the fragment file path for one node."""
    return NODE_PATHS[node_id] / f"fragment_{fragment_id}.bin"


def fragment_bytes(file_bytes: bytes, parts: int) -> list[bytes]:
    """Split file bytes into near-equal parts."""
    chunk_size = max(1, math.ceil(len(file_bytes) / parts))
    return [
        file_bytes[index : index + chunk_size]
        for index in range(0, len(file_bytes), chunk_size)
    ]


def healthy_nodes() -> list[str]:
    """Return node IDs that are currently active."""
    return [
        node_id
        for node_id, node in st.session_state.nodes.items()
        if node["status"] == "Active"
    ]


def store_fragment(node_id: str, fragment_id: int, data: bytes) -> None:
    """Store one fragment on one node and update the in-memory model."""
    node_fragment_path(node_id, fragment_id).write_bytes(data)

    if fragment_id not in st.session_state.nodes[node_id]["fragments"]:
        st.session_state.nodes[node_id]["fragments"].append(fragment_id)
        st.session_state.nodes[node_id]["fragments"].sort()

    holders = st.session_state.fragments[fragment_id]["nodes"]
    if node_id not in holders:
        holders.append(node_id)
        holders.sort()


def remove_fragment(node_id: str, fragment_id: int) -> None:
    """Remove one fragment from one node and update the in-memory model."""
    fragment_path = node_fragment_path(node_id, fragment_id)
    if fragment_path.exists():
        fragment_path.unlink()

    if fragment_id in st.session_state.nodes[node_id]["fragments"]:
        st.session_state.nodes[node_id]["fragments"].remove(fragment_id)

    if node_id in st.session_state.fragments[fragment_id]["nodes"]:
        st.session_state.fragments[fragment_id]["nodes"].remove(node_id)


def reset_simulation(clear_storage: bool = True) -> None:
    """Reset the running simulation state."""
    if clear_storage:
        clear_node_files()

    st.session_state.nodes = build_default_nodes()
    st.session_state.fragments = {}
    st.session_state.file_name = None
    st.session_state.file_size = 0
    st.session_state.upload_signature = None
    st.session_state.uploader_key += 1
    st.session_state.reconstructed_bytes = None
    st.session_state.network_ready = False
    st.session_state.system_state = "Healthy"
    st.session_state.status_text = None
    st.session_state.status_level = "info"
    st.session_state.expiry_time = None
    st.session_state.show_schedule_popup = False
    st.session_state.show_expiry_popup = False
    st.session_state.self_destructed = False


def ingest_file(uploaded_file) -> None:
    """Upload, fragment, and distribute a file across secure nodes."""
    clear_node_files()
    st.session_state.nodes = build_default_nodes()
    st.session_state.fragments = {}
    st.session_state.reconstructed_bytes = None
    st.session_state.self_destructed = False

    file_bytes = uploaded_file.getvalue()
    parts = random.randint(3, 5)
    chunks = fragment_bytes(file_bytes, parts)

    add_log(f"Upload received for {uploaded_file.name} ({len(file_bytes)} bytes).", "success")
    add_log("Fragmenting data for secure distribution.", "info")

    for index, chunk in enumerate(chunks, start=1):
        st.session_state.fragments[index] = {
            "size": len(chunk),
            "data": chunk,
            "nodes": [],
        }
        assigned_nodes = random.sample(NODE_IDS, REDUNDANCY_COPIES)
        for node_id in assigned_nodes:
            store_fragment(node_id, index, chunk)
        add_log(
            f"Fragment {index} distributed to {assigned_nodes[0]} and {assigned_nodes[1]}.",
            "success",
        )

    add_log("Secure node network is now monitoring the distributed file.", "info")
    st.session_state.file_name = uploaded_file.name
    st.session_state.file_size = len(file_bytes)
    st.session_state.upload_signature = f"{uploaded_file.name}:{uploaded_file.size}"
    st.session_state.network_ready = True
    st.session_state.system_state = "Healthy"
    st.session_state.show_schedule_popup = True
    st.session_state.show_expiry_popup = False
    set_status("File uploaded successfully. Set the data lifespan to arm the timer.", "success")


def schedule_expiry(expiry_date, expiry_clock) -> bool:
    """Combine date and time into a valid future expiry datetime."""
    scheduled = datetime.combine(expiry_date, expiry_clock)
    if scheduled <= datetime.now():
        add_log("Deletion schedule rejected because the selected date and time are in the past.", "error")
        set_status("Select a future expiry date and time.", "error")
        return False

    st.session_state.selected_expiry_date = expiry_date
    st.session_state.selected_expiry_time = expiry_clock
    st.session_state.expiry_time = scheduled
    st.session_state.show_schedule_popup = False
    st.session_state.show_expiry_popup = False
    add_log(
        f"File scheduled for deletion at {scheduled.strftime('%Y-%m-%d %H:%M')}.",
        "success",
    )
    set_status(
        f"File scheduled for deletion at {scheduled.strftime('%Y-%m-%d %H:%M')}.",
        "success",
    )
    return True


def countdown_text() -> str:
    """Render the current countdown."""
    expiry_time = st.session_state.expiry_time
    if expiry_time is None:
        return "Not Armed"

    remaining = max(0, int((expiry_time - datetime.now()).total_seconds()))
    minutes, seconds = divmod(remaining, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def scheduled_expiry_text() -> str:
    """Render the selected scheduled deletion time."""
    if st.session_state.expiry_time is None:
        return "Not Scheduled"
    return st.session_state.expiry_time.strftime("%Y-%m-%d %H:%M")


def evaluate_timer() -> None:
    """Open the expiry popup when the active lifespan ends."""
    expiry_time = st.session_state.expiry_time
    if expiry_time is None or st.session_state.show_expiry_popup:
        return

    if datetime.now() >= expiry_time and st.session_state.network_ready:
        st.session_state.show_expiry_popup = True
        st.session_state.system_state = "Failure Detected"
        add_log("File lifespan expired.", "warning")
        set_status("File expired. Reset the timer or delete the file.", "error")


def simulate_node_failure() -> None:
    """Fail one active node and remove its fragments."""
    candidates = [
        node_id
        for node_id, node in st.session_state.nodes.items()
        if node["status"] == "Active" and node["fragments"]
    ]

    if not candidates:
        add_log("Failure simulation skipped because no active node contains fragments.", "warning")
        set_status("No active secure unit is available for failure simulation.", "error")
        return

    failed_node = random.choice(candidates)
    st.session_state.nodes[failed_node]["status"] = "Failed"
    failed_fragments = list(st.session_state.nodes[failed_node]["fragments"])

    add_log(f"Node failure detected in {failed_node}.", "error")
    add_log("Missing fragments identified. Rerouting protocol is waiting for repair.", "info")

    for fragment_id in failed_fragments:
        remove_fragment(failed_node, fragment_id)

    st.session_state.system_state = "Failure Detected"
    set_status("Node failure detected. Run self-healing to restore redundancy.", "error")


def heal_network() -> None:
    """Restore missing fragments and return the system to a stable state."""
    if not st.session_state.network_ready:
        set_status("Upload a file before running self-healing.", "error")
        return

    st.session_state.system_state = "Repairing"
    add_log("Repair cycle started. Reconstructing missing fragments using redundancy.", "info")

    repaired = False

    for fragment_id, fragment in st.session_state.fragments.items():
        surviving_nodes = list(fragment["nodes"])
        if not surviving_nodes:
            add_log(
                f"Fragment {fragment_id} cannot be recovered because all copies were lost.",
                "error",
            )
            continue

        available_targets = [
            node_id for node_id in healthy_nodes() if node_id not in surviving_nodes
        ]

        while len(fragment["nodes"]) < REDUNDANCY_COPIES and available_targets:
            target_node = available_targets.pop(0)
            store_fragment(target_node, fragment_id, fragment["data"])
            repaired = True
            add_log(f"Fragment {fragment_id} restored to {target_node}.", "success")

    # Bring failed nodes back online after the repair cycle for monitoring continuity.
    for node_id, node in st.session_state.nodes.items():
        if node["status"] == "Failed":
            node["status"] = "Active"

    st.session_state.reconstructed_bytes = b"".join(
        st.session_state.fragments[fragment_id]["data"]
        for fragment_id in sorted(st.session_state.fragments)
    )

    unresolved_loss = any(
        len(fragment["nodes"]) == 0 for fragment in st.session_state.fragments.values()
    )

    if unresolved_loss:
        st.session_state.system_state = "Failure Detected"
        add_log("Repair cycle ended with unresolved fragment loss.", "error")
        set_status("Repair incomplete. Some fragments could not be recovered.", "error")
        return

    if repaired:
        st.session_state.system_state = "Restored"
        add_log("Self-healing complete. Redundancy restored and monitoring resumed.", "success")
        set_status("Self-healing complete. System restored.", "success")
    else:
        st.session_state.system_state = "Healthy"
        add_log("Repair check complete. No missing fragments required recovery.", "info")
        set_status("System is already healthy.", "info")


def run_self_destruct() -> None:
    """Delete all fragments from all nodes with a visible log countdown."""
    st.session_state.system_state = "Destroyed"
    add_log("Self-destruct mode activated.", "warning")

    for tick in [3, 2, 1]:
        add_log(f"Secure deletion countdown: {tick}", "warning")
        time.sleep(0.35)

    clear_node_files()

    for node in st.session_state.nodes.values():
        node["fragments"] = []
        node["status"] = "Active"

    st.session_state.fragments = {}
    st.session_state.reconstructed_bytes = None
    st.session_state.network_ready = False
    st.session_state.self_destructed = True
    st.session_state.expiry_time = None
    st.session_state.show_schedule_popup = False
    st.session_state.show_expiry_popup = False
    st.session_state.file_name = None
    st.session_state.file_size = 0
    st.session_state.upload_signature = None
    st.session_state.uploader_key += 1

    add_log("All data securely deleted from every storage unit.", "error")
    set_status("All data securely deleted.", "success")


def render_styles() -> None:
    """Inject custom styles for the dashboard."""
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(34,197,94,0.12), transparent 24%),
                radial-gradient(circle at top right, rgba(14,165,233,0.12), transparent 22%),
                linear-gradient(180deg, #020617 0%, #09111f 55%, #111827 100%);
        }
        .block-container {
            max-width: 1380px;
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }
        .hero-card, .panel-card, .popup-card {
            background: rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(51, 65, 85, 0.82);
            border-radius: 20px;
            box-shadow: 0 18px 36px rgba(2, 6, 23, 0.28);
        }
        .hero-card {
            padding: 24px;
            border-color: rgba(34, 197, 94, 0.36);
        }
        .panel-card {
            padding: 18px;
            height: 100%;
        }
        .popup-card {
            padding: 22px;
            max-width: 680px;
            margin: 0 auto 1rem auto;
            border-color: rgba(14,165,233,0.45);
        }
        .section-title {
            color: #f8fafc;
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 0.8rem;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin-top: 16px;
        }
        .summary-item {
            background: rgba(2, 6, 23, 0.54);
            border: 1px solid rgba(51, 65, 85, 0.8);
            border-radius: 16px;
            padding: 14px;
        }
        .summary-label {
            color: #94a3b8;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .summary-value {
            color: #f8fafc;
            font-size: 18px;
            font-weight: 700;
            margin-top: 6px;
            word-break: break-word;
        }
        .state-chip {
            display: inline-block;
            margin-top: 10px;
            padding: 10px 16px;
            border-radius: 999px;
            font-weight: 700;
            border: 1px solid currentColor;
        }
        .node-card {
            border-radius: 18px;
            padding: 18px;
            min-height: 165px;
            margin-bottom: 14px;
        }
        .node-card.active {
            background: linear-gradient(180deg, rgba(6,95,70,0.52), rgba(6,78,59,0.16));
            border: 1px solid rgba(34,197,94,0.74);
        }
        .node-card.failed {
            background: linear-gradient(180deg, rgba(127,29,29,0.58), rgba(69,10,10,0.18));
            border: 1px solid rgba(248,113,113,0.82);
        }
        .node-title {
            color: #f8fafc;
            font-size: 1.05rem;
            font-weight: 700;
        }
        .node-status {
            margin-top: 4px;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 700;
        }
        .node-meta {
            color: #dbeafe;
            font-size: 14px;
            line-height: 1.8;
            margin-top: 12px;
        }
        .network-strip {
            margin-bottom: 14px;
            color: #7dd3fc;
            text-align: center;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-size: 12px;
        }
        .route-card {
            background: rgba(2, 6, 23, 0.55);
            border: 1px solid rgba(51, 65, 85, 0.82);
            border-radius: 14px;
            padding: 12px 14px;
            margin-bottom: 10px;
        }
        .log-box {
            background: rgba(2, 6, 23, 0.84);
            border: 1px solid rgba(51, 65, 85, 0.8);
            border-radius: 16px;
            padding: 14px;
            min-height: 420px;
            max-height: 620px;
            overflow-y: auto;
            white-space: pre-wrap;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            color: #d1fae5;
        }
        .big-download button {
            width: 100%;
            min-height: 3.35rem;
            font-size: 1rem;
            font-weight: 700;
        }
        div[data-testid="stFileUploader"] section {
            border: 1px dashed rgba(56, 189, 248, 0.62);
            border-radius: 16px;
            background: rgba(2, 6, 23, 0.3);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    """Render the top header and system overview."""
    state_colors = {
        "Healthy": "#86efac",
        "Failure Detected": "#fca5a5",
        "Repairing": "#93c5fd",
        "Restored": "#67e8f9",
        "Destroyed": "#fbbf24",
    }
    state_color = state_colors.get(st.session_state.system_state, "#cbd5e1")
    file_label = st.session_state.file_name or "No file loaded"
    size_label = f"{st.session_state.file_size} bytes" if st.session_state.file_size else "0 bytes"

    st.markdown(
        f"""
        <div class="hero-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:20px;flex-wrap:wrap;">
                <div>
                    <div style="color:#86efac;font-size:13px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;">
                        🌐 Security Simulation Dashboard
                    </div>
                    <div style="color:#f8fafc;font-size:2rem;font-weight:800;margin-top:8px;">
                        MycoGuard Bio-Inspired Security System
                    </div>
                    <div style="color:#94a3b8;max-width:780px;margin-top:8px;">
                        Distributed file protection inspired by mycelium networks, resilience through redundancy-based repair, and apoptosis-style secure deletion.
                    </div>
                    <div class="state-chip" style="color:{state_color};">System State: {st.session_state.system_state}</div>
                </div>
                <div style="min-width:250px;">
                    <div style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:0.08em;">Time Remaining</div>
                    <div style="color:#f8fafc;font-size:1.6rem;font-weight:800;margin-top:8px;">{countdown_text()}</div>
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
                    <div class="summary-value">{len(st.session_state.fragments)}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Active Nodes</div>
                    <div class="summary-value">{len(healthy_nodes())} / 4</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_popup() -> None:
    """Render the schedule setup and expiry popups."""
    if st.session_state.show_schedule_popup:
        left, center, right = st.columns([1, 1.5, 1])
        with center:
            st.markdown('<div class="popup-card">', unsafe_allow_html=True)
            st.markdown("### ⏱️ Set Destruction Schedule")
            st.info("Choose the date and time when MycoGuard should ask whether to delete the protected file.")
            controls = st.columns(2)
            expiry_date = controls[0].date_input(
                "Select Expiry Date",
                value=st.session_state.selected_expiry_date,
                min_value=datetime.now().date(),
                key="expiry_date_input",
            )
            expiry_clock = controls[1].time_input(
                "Select Expiry Time",
                value=st.session_state.selected_expiry_time,
                key="expiry_time_input",
            )
            preview_dt = datetime.combine(expiry_date, expiry_clock)
            st.write(f"Scheduled deletion time: `{preview_dt.strftime('%Y-%m-%d %H:%M')}`")
            if st.button("Schedule Deletion", use_container_width=True, type="primary"):
                if schedule_expiry(expiry_date, expiry_clock):
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.show_expiry_popup:
        left, center, right = st.columns([1, 1.5, 1])
        with center:
            st.markdown('<div class="popup-card">', unsafe_allow_html=True)
            st.markdown("### ⚠️ File Expired")
            st.error("The configured file lifespan has ended.")
            st.write("Choose whether to extend protection or securely delete the file.")
            actions = st.columns(2)
            if actions[0].button("Reset Timer", use_container_width=True):
                st.session_state.show_schedule_popup = True
                st.session_state.show_expiry_popup = False
                st.session_state.system_state = "Healthy"
                add_log("Expiry schedule reset requested after file expiry.", "success")
                set_status("Choose a new expiry date and time.", "info")
                st.rerun()
            if actions[1].button("Delete File", use_container_width=True, type="primary"):
                run_self_destruct()
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


def render_upload_panel() -> None:
    """Render the primary upload section at the top center of the dashboard."""
    left, center, right = st.columns([0.7, 1.6, 0.7])
    with center:
        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📤 Secure File Ingestion</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload a file to distribute across secure storage units",
            key=f"uploader_{st.session_state.uploader_key}",
        )

        if uploaded_file is not None:
            signature = f"{uploaded_file.name}:{uploaded_file.size}"
            if st.session_state.upload_signature != signature:
                ingest_file(uploaded_file)
                st.rerun()

        if st.session_state.file_name:
            st.success("File uploaded successfully")
            st.markdown(f"**File:** `{st.session_state.file_name}`")
            st.markdown(f"**Size:** `{st.session_state.file_size} bytes`")
            st.markdown("**Pipeline:** `Upload → Fragment → Distribute → Monitor`")
        else:
            st.info("Start the simulation by uploading a file into the MycoGuard network.")

        st.markdown("</div>", unsafe_allow_html=True)


def render_action_feedback() -> None:
    """Render the single feedback area below the action buttons."""
    if not st.session_state.status_text:
        return
    if st.session_state.status_level == "success":
        st.success(st.session_state.status_text)
    elif st.session_state.status_level == "error":
        st.error(st.session_state.status_text)
    else:
        st.info(st.session_state.status_text)


def render_control_panel() -> None:
    """Render the left-side control center."""
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🎛️ Control Center</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.write("**Timer Settings**")
    st.write(f"Scheduled deletion: `{scheduled_expiry_text()}`")
    st.write(f"Time remaining: `{countdown_text()}`")
    if st.button("🗓️ Update Schedule", use_container_width=True, disabled=not st.session_state.file_name):
        st.session_state.show_schedule_popup = True
        st.session_state.show_expiry_popup = False
        set_status("Select a new expiry date and time.", "info")
        st.rerun()

    st.markdown("---")
    st.write("**Actions**")
    if st.button("⚠️ Simulate Node Failure", use_container_width=True, disabled=not st.session_state.network_ready):
        simulate_node_failure()

    if st.button("🧬 Run Self-Healing", use_container_width=True, disabled=not st.session_state.network_ready):
        heal_network()

    if st.button("💥 Activate Self-Destruct", use_container_width=True, disabled=not st.session_state.network_ready):
        run_self_destruct()
        st.rerun()

    if st.button("♻️ Reset Simulation", use_container_width=True):
        reset_simulation()
        add_log("Simulation reset. Dashboard returned to idle mode.", "warning")
        st.rerun()

    st.markdown("---")
    render_action_feedback()
    st.markdown("</div>", unsafe_allow_html=True)


def render_file_panel() -> None:
    """Render file info and the prominent download section."""
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📦 File Status</div>', unsafe_allow_html=True)

    if st.session_state.file_name:
        st.markdown(f"**File:** `{st.session_state.file_name}`")
        st.markdown(f"**Size:** `{st.session_state.file_size} bytes`")
        st.markdown(f"**Protection Status:** `{st.session_state.system_state}`")
        st.markdown(f"**File scheduled for deletion at:** `{scheduled_expiry_text()}`")
        st.markdown(f"**Time remaining:** `{countdown_text()}`")
    elif st.session_state.self_destructed:
        st.error("The protected file was securely deleted.")
    else:
        st.info("No file has been uploaded yet.")

    st.markdown("---")
    st.markdown("**Recovery Access**")
    st.markdown('<div class="big-download">', unsafe_allow_html=True)
    if st.session_state.reconstructed_bytes is not None:
        st.download_button(
            "Download Reconstructed File",
            data=st.session_state.reconstructed_bytes,
            file_name=f"recovered_{st.session_state.file_name or 'file'}",
            use_container_width=True,
            type="primary",
        )
    else:
        st.button(
            "Download Reconstructed File",
            use_container_width=True,
            disabled=True,
            key="download_disabled",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.reconstructed_bytes is not None:
        st.success("Reconstructed file is ready for download.")
    else:
        st.info("Run self-healing to reconstruct the file and enable download.")

    st.markdown("</div>", unsafe_allow_html=True)


def render_network_panel() -> None:
    """Render the core secure node network visualization."""
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔒 Secure Node Network</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="network-strip">node1 ●────● node2 ●────● node3 ●────● node4</div>',
        unsafe_allow_html=True,
    )

    top_row = st.columns(2, gap="medium")
    bottom_row = st.columns(2, gap="medium")
    all_columns = top_row + bottom_row

    for col, node_id in zip(all_columns, NODE_IDS):
        node = st.session_state.nodes[node_id]
        active = node["status"] == "Active"
        class_name = "active" if active else "failed"
        status_color = "#86efac" if active else "#fca5a5"
        fragment_list = ", ".join(str(item) for item in node["fragments"]) if node["fragments"] else "None"

        with col:
            st.markdown(
                f"""
                <div class="node-card {class_name}">
                    <div class="node-title">🔒 {node['label']}</div>
                    <div class="node-status" style="color:{status_color};">{node['status']}</div>
                    <div class="node-meta">
                        Fragment count: <b>{len(node['fragments'])}</b><br>
                        Stored fragments: <b>{fragment_list}</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("**Data Flow**")
    if not st.session_state.fragments:
        st.info("Upload a file to start the flow: Upload → Fragment → Distribute → Monitor.")
    else:
        for fragment_id in sorted(st.session_state.fragments):
            fragment = st.session_state.fragments[fragment_id]
            holders = ", ".join(fragment["nodes"]) if fragment["nodes"] else "Missing"
            st.markdown(
                f"""
                <div class="route-card">
                    <div style="color:#f8fafc;font-weight:700;">Fragment {fragment_id}</div>
                    <div style="color:#93c5fd;margin-top:6px;">Size: {fragment['size']} bytes</div>
                    <div style="color:#cbd5e1;margin-top:4px;">Current nodes: <b>{holders}</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


def render_logs_panel() -> None:
    """Render the single structured system log panel."""
    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📜 System Logs</div>', unsafe_allow_html=True)
    if st.session_state.logs:
        log_text = "\n".join(st.session_state.logs)
    else:
        log_text = "[system] Awaiting upload event..."
    st.markdown(f'<div class="log-box">{log_text}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    """Main Streamlit entry point."""
    st.set_page_config(
        page_title="MycoGuard Bio-Inspired Security System",
        page_icon="🔒",
        layout="wide",
    )
    ensure_nodes()
    init_state()
    render_styles()
    evaluate_timer()

    render_header()
    st.markdown("")
    render_popup()
    render_upload_panel()
    st.markdown("")

    left_col, center_col, right_col = st.columns([0.24, 0.5, 0.26], gap="large")

    with left_col:
        render_control_panel()

    with center_col:
        render_file_panel()
        st.markdown("")
        render_network_panel()

    with right_col:
        render_logs_panel()


if __name__ == "__main__":
    main()
