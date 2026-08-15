import streamlit as st
import sqlite3
import os
import shutil
from datetime import date, datetime, timedelta
import pandas as pd

# =========================================================
# AUTOHISTORY - DIGITAL VEHICLE SERVICE PASSPORT
# Complete self-contained Streamlit application
# =========================================================

st.set_page_config(
    page_title="AutoHistory",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# CONFIG
# =========================================================

DB_FILE = "autohistory.db"
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            registration TEXT NOT NULL UNIQUE,
            manufacturing_year INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            service_type TEXT NOT NULL,
            service_date TEXT NOT NULL,
            odometer INTEGER DEFAULT 0,
            amount REAL DEFAULT 0,
            workshop TEXT,
            notes TEXT,
            next_service_date TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            document_type TEXT,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
        )
    """)

    conn.commit()

    # Add a demo vehicle only if database is completely empty
    count = cursor.execute(
        "SELECT COUNT(*) AS count FROM vehicles"
    ).fetchone()["count"]

    if count == 0:
        cursor.execute("""
            INSERT INTO vehicles
            (name, registration, manufacturing_year, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            "Hyundai i20",
            "TS09 AB 1234",
            2022,
            datetime.now().isoformat()
        ))
        conn.commit()

    conn.close()


init_database()


# =========================================================
# DATABASE FUNCTIONS
# =========================================================

def get_vehicles():
    conn = get_connection()
    rows = conn.execute("""
        SELECT *
        FROM vehicles
        ORDER BY id DESC
    """).fetchall()
    conn.close()
    return rows


def get_vehicle(vehicle_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT *
        FROM vehicles
        WHERE id = ?
    """, (vehicle_id,)).fetchone()
    conn.close()
    return row


def add_vehicle(name, registration, manufacturing_year):
    conn = get_connection()

    try:
        conn.execute("""
            INSERT INTO vehicles
            (name, registration, manufacturing_year, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            registration.upper(),
            manufacturing_year,
            datetime.now().isoformat()
        ))

        conn.commit()
        return True, "Vehicle added successfully."

    except sqlite3.IntegrityError:
        return False, "Registration number already exists."

    finally:
        conn.close()


def delete_vehicle(vehicle_id):
    conn = get_connection()

    services = conn.execute("""
        SELECT id FROM services WHERE vehicle_id = ?
    """, (vehicle_id,)).fetchall()

    documents = conn.execute("""
        SELECT filepath FROM documents WHERE vehicle_id = ?
    """, (vehicle_id,)).fetchall()

    for doc in documents:
        path = doc["filepath"]
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    conn.execute(
        "DELETE FROM services WHERE vehicle_id = ?",
        (vehicle_id,)
    )

    conn.execute(
        "DELETE FROM documents WHERE vehicle_id = ?",
        (vehicle_id,)
    )

    conn.execute(
        "DELETE FROM vehicles WHERE id = ?",
        (vehicle_id,)
    )

    conn.commit()
    conn.close()


def get_services(vehicle_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM services
        WHERE vehicle_id = ?
        ORDER BY service_date DESC, id DESC
    """, (vehicle_id,)).fetchall()

    conn.close()
    return rows


def add_service(
    vehicle_id,
    service_type,
    service_date,
    odometer,
    amount,
    workshop,
    notes,
    next_service_date
):
    conn = get_connection()

    conn.execute("""
        INSERT INTO services
        (
            vehicle_id,
            service_type,
            service_date,
            odometer,
            amount,
            workshop,
            notes,
            next_service_date,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        vehicle_id,
        service_type,
        service_date,
        odometer,
        amount,
        workshop,
        notes,
        next_service_date,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def delete_service(service_id):
    conn = get_connection()

    conn.execute(
        "DELETE FROM services WHERE id = ?",
        (service_id,)
    )

    conn.commit()
    conn.close()


def get_documents(vehicle_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM documents
        WHERE vehicle_id = ?
        ORDER BY uploaded_at DESC
    """, (vehicle_id,)).fetchall()

    conn.close()
    return rows


def add_document(
    vehicle_id,
    filename,
    filepath,
    document_type
):
    conn = get_connection()

    conn.execute("""
        INSERT INTO documents
        (
            vehicle_id,
            filename,
            filepath,
            document_type,
            uploaded_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        vehicle_id,
        filename,
        filepath,
        document_type,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def delete_document(document_id):
    conn = get_connection()

    row = conn.execute("""
        SELECT filepath
        FROM documents
        WHERE id = ?
    """, (document_id,)).fetchone()

    if row and os.path.exists(row["filepath"]):
        try:
            os.remove(row["filepath"])
        except:
            pass

    conn.execute(
        "DELETE FROM documents WHERE id = ?",
        (document_id,)
    )

    conn.commit()
    conn.close()


# =========================================================
# ANALYTICS
# =========================================================

def service_dataframe(vehicle_id):
    services = get_services(vehicle_id)

    if not services:
        return pd.DataFrame()

    data = []

    for service in services:
        data.append({
            "Date": service["service_date"],
            "Service": service["service_type"],
            "Odometer": service["odometer"],
            "Amount": service["amount"],
            "Workshop": service["workshop"] or "",
            "Notes": service["notes"] or ""
        })

    df = pd.DataFrame(data)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    df["Odometer"] = pd.to_numeric(
        df["Odometer"],
        errors="coerce"
    ).fillna(0)

    return df


def total_spending(vehicle_id):
    services = get_services(vehicle_id)

    return sum(
        float(service["amount"] or 0)
        for service in services
    )


def get_next_service(vehicle_id):
    services = get_services(vehicle_id)

    future_dates = []

    today = date.today()

    for service in services:
        next_date = service["next_service_date"]

        if next_date:
            try:
                d = datetime.strptime(
                    next_date,
                    "%Y-%m-%d"
                ).date()

                if d >= today:
                    future_dates.append(
                        (d, service)
                    )

            except:
                pass

    if not future_dates:
        return None

    future_dates.sort(key=lambda x: x[0])

    return future_dates[0]


# =========================================================
# AI MAINTENANCE RECOMMENDATIONS
# =========================================================

def maintenance_recommendations(vehicle_id):
    vehicle = get_vehicle(vehicle_id)
    services = get_services(vehicle_id)

    recommendations = []

    if not services:
        recommendations.append(
            (
                "🔧",
                "Start your service history",
                "No service records are available yet. "
                "Add your first service record to enable "
                "maintenance insights."
            )
        )

        return recommendations

    today = date.today()

    latest_service = services[0]

    # -----------------------------------------------------
    # Next service date
    # -----------------------------------------------------

    if latest_service["next_service_date"]:

        try:
            next_date = datetime.strptime(
                latest_service["next_service_date"],
                "%Y-%m-%d"
            ).date()

            days_left = (next_date - today).days

            if days_left < 0:
                recommendations.append(
                    (
                        "🚨",
                        "Service overdue",
                        f"The next service was due on "
                        f"{next_date.strftime('%d %b %Y')}."
                    )
                )

            elif days_left <= 30:
                recommendations.append(
                    (
                        "⏰",
                        "Service due soon",
                        f"Your next service is due in "
                        f"{days_left} day(s)."
                    )
                )

            else:
                recommendations.append(
                    (
                        "✅",
                        "Maintenance schedule",
                        f"Next service is planned for "
                        f"{next_date.strftime('%d %b %Y')}."
                    )
                )

        except:
            pass

    # -----------------------------------------------------
    # Oil change
    # -----------------------------------------------------

    oil_services = [
        s for s in services
        if "oil" in (s["service_type"] or "").lower()
    ]

    if oil_services:
        try:
            last_oil = datetime.strptime(
                oil_services[0]["service_date"],
                "%Y-%m-%d"
            ).date()

            days = (today - last_oil).days

            if days > 180:
                recommendations.append(
                    (
                        "🛢️",
                        "Check engine oil",
                        "More than 6 months have passed "
                        "since the recorded oil service."
                    )
                )

        except:
            pass

    # -----------------------------------------------------
    # Spending analysis
    # -----------------------------------------------------

    total = total_spending(vehicle_id)

    if total > 20000:
        recommendations.append(
            (
                "💰",
                "High maintenance spending",
                f"Recorded spending has reached "
                f"₹{total:,.0f}. Review recurring repair "
                f"items and service intervals."
            )
        )

    # -----------------------------------------------------
    # Service frequency
    # -----------------------------------------------------

    if len(services) >= 3:
        recommendations.append(
            (
                "📊",
                "Regular maintenance detected",
                "Your vehicle has multiple service records. "
                "Continue maintaining the same service schedule."
            )
        )

    # -----------------------------------------------------
    # General recommendations
    # -----------------------------------------------------

    recommendations.append(
        (
            "🛞",
            "Tyre check",
            "Periodically check tyre pressure, tread depth "
            "and wheel alignment."
        )
    )

    recommendations.append(
        (
            "🔋",
            "Battery check",
            "Check battery health periodically, especially "
            "before long trips."
        )
    )

    recommendations.append(
        (
            "🛑",
            "Brake inspection",
            "Inspect brake pads and brake fluid during "
            "regular servicing."
        )
    )

    return recommendations


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.main {
    background-color: #f8fafc;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

.app-title {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 4px;
}

.app-subtitle {
    color: #64748b;
    font-size: 17px;
    margin-bottom: 25px;
}

.card {
    background: white;
    padding: 22px;
    border-radius: 16px;
    border: 1px solid #e2e8f0;
    margin-bottom: 18px;
}

.metric-card {
    background: white;
    padding: 20px;
    border-radius: 16px;
    border: 1px solid #e2e8f0;
    min-height: 130px;
}

.metric-title {
    color: #64748b;
    font-size: 14px;
}

.metric-value {
    font-size: 30px;
    font-weight: 800;
    margin-top: 8px;
}

.section-title {
    font-size: 27px;
    font-weight: 750;
    margin-top: 20px;
    margin-bottom: 15px;
}

.small-muted {
    color: #64748b;
}

.reminder {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 15px;
}

.success-box {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 15px;
}

.ai-box {
    background: #f8f7ff;
    border: 1px solid #ddd6fe;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 14px;
}

.footer {
    text-align: center;
    color: #64748b;
    padding: 30px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# SIDEBAR
# =========================================================

vehicles = get_vehicles()

st.sidebar.markdown("""
<div style="font-size:30px;font-weight:800;">
🚘 AutoHistory
</div>
<div style="color:#64748b;margin-bottom:25px;">
Your Digital Vehicle Service Passport
</div>
""", unsafe_allow_html=True)

if vehicles:

    vehicle_labels = [
        f"{v['name']} — {v['registration']}"
        for v in vehicles
    ]

    selected_label = st.sidebar.selectbox(
        "🚘 Select Vehicle",
        vehicle_labels
    )

    selected_index = vehicle_labels.index(
        selected_label
    )

    selected_vehicle = vehicles[selected_index]
    vehicle_id = selected_vehicle["id"]

else:
    selected_vehicle = None
    vehicle_id = None

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "🚘 My Vehicles",
        "🔧 Service History",
        "📄 Documents",
        "📊 Analytics",
        "⏰ Maintenance",
        "🤖 AI Assistant"
    ]
)

st.sidebar.markdown("---")

st.sidebar.info(
    "Keep your complete vehicle history "
    "safe and organized."
)


# =========================================================
# HEADER
# =========================================================

st.markdown("""
<div class="app-title">🚘 AutoHistory</div>
<div class="app-subtitle">
Digital Vehicle Service Passport
</div>
""", unsafe_allow_html=True)


# =========================================================
# NO VEHICLE
# =========================================================

if selected_vehicle is None:

    st.warning(
        "No vehicle found. Please add a vehicle "
        "from My Vehicles."
    )

    st.stop()


# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Dashboard":

    services = get_services(vehicle_id)
    documents = get_documents(vehicle_id)

    total_records = len(services) + len(documents)
    total_spent = total_spending(vehicle_id)

    st.markdown(
        '<div class="section-title">Vehicle Overview</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Vehicle</div>
            <div class="metric-value">
                {selected_vehicle["name"]}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Registration</div>
            <div class="metric-value">
                {selected_vehicle["registration"]}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">
                Manufacturing Year
            </div>
            <div class="metric-value">
                {selected_vehicle["manufacturing_year"]}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">
                Total Records
            </div>
            <div class="metric-value">
                {total_records}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        '<div class="section-title">Quick Statistics</div>',
        unsafe_allow_html=True
    )

    q1, q2, q3, q4 = st.columns(4)

    with q1:
        st.metric(
            "🔧 Services",
            len(services)
        )

    with q2:
        st.metric(
            "📄 Documents",
            len(documents)
        )

    with q3:
        st.metric(
            "💰 Total Spent",
            f"₹{total_spent:,.2f}"
        )

    with q4:

        if services:
            latest = services[0]["service_date"]
            st.metric(
                "🔧 Last Service",
                latest
            )
        else:
            st.metric(
                "🔧 Last Service",
                "No records"
            )

    # Reminder

    next_service = get_next_service(vehicle_id)

    if next_service:

        next_date, service = next_service
        days_left = (next_date - date.today()).days

        st.markdown(
            '<div class="section-title">'
            '⏰ Maintenance Reminder'
            '</div>',
            unsafe_allow_html=True
        )

        if days_left <= 30:

            st.markdown(f"""
            <div class="reminder">
                <b>⚠️ Upcoming Service</b><br><br>
                Service: {service["service_type"]}<br>
                Due Date: {next_date.strftime("%d %b %Y")}<br>
                Days Remaining: {days_left}
            </div>
            """, unsafe_allow_html=True)

        else:

            st.markdown(f"""
            <div class="success-box">
                <b>✅ Maintenance Scheduled</b><br><br>
                Next service:
                {next_date.strftime("%d %b %Y")}<br>
                Days Remaining: {days_left}
            </div>
            """, unsafe_allow_html=True)

    # Recent Service

    st.markdown(
        '<div class="section-title">'
        '🔧 Recent Service'
        '</div>',
        unsafe_allow_html=True
    )

    if services:

        recent = services[0]

        st.markdown(f"""
        <div class="card">
            <h3>{recent["service_type"]}</h3>
            <p>📅 {recent["service_date"]}</p>
            <p>💰 ₹{float(recent["amount"] or 0):,.2f}</p>
            <p>🏪 {recent["workshop"] or "Not specified"}</p>
        </div>
        """, unsafe_allow_html=True)

    else:

        st.info(
            "No service records found. "
            "Add your first service from Service History."
        )

    # Recent Document

    st.markdown(
        '<div class="section-title">'
        '📄 Recent Document'
        '</div>',
        unsafe_allow_html=True
    )

    if documents:

        doc = documents[0]

        st.markdown(f"""
        <div class="card">
            <h3>📄 {doc["filename"]}</h3>
            <p>
                Type: {doc["document_type"] or "Document"}
            </p>
            <p>
                Uploaded: {doc["uploaded_at"][:10]}
            </p>
        </div>
        """, unsafe_allow_html=True)

    else:

        st.info(
            "No documents uploaded yet."
        )


# =========================================================
# MY VEHICLES
# =========================================================

elif page == "🚘 My Vehicles":

    st.markdown(
        '<div class="section-title">🚘 My Vehicles</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Manage all your vehicles from one place."
    )

    current_vehicles = get_vehicles()

    for vehicle in current_vehicles:

        services = get_services(vehicle["id"])
        documents = get_documents(vehicle["id"])

        with st.container(border=True):

            a, b, c = st.columns([2, 2, 1])

            with a:
                st.subheader(
                    f"🚘 {vehicle['name']}"
                )
                st.write(
                    f"Registration: "
                    f"**{vehicle['registration']}**"
                )

            with b:
                st.write(
                    f"Manufacturing Year: "
                    f"**{vehicle['manufacturing_year']}**"
                )

                st.write(
                    f"🔧 {len(services)} services  |  "
                    f"📄 {len(documents)} documents"
                )

            with c:

                if st.button(
                    "🗑️ Delete",
                    key=f"delete_vehicle_{vehicle['id']}"
                ):

                    delete_vehicle(vehicle["id"])

                    st.success(
                        "Vehicle deleted."
                    )

                    st.rerun()

    st.markdown("---")

    st.subheader("➕ Add New Vehicle")

    with st.form("add_vehicle_form"):

        name = st.text_input(
            "Vehicle Name",
            placeholder="Example: Hyundai i20"
        )

        registration = st.text_input(
            "Registration Number",
            placeholder="Example: TS09 AB 1234"
        )

        manufacturing_year = st.number_input(
            "Manufacturing Year",
            min_value=1980,
            max_value=date.today().year,
            value=2024,
            step=1
        )

        submitted = st.form_submit_button(
            "💾 Save Vehicle",
            use_container_width=True
        )

        if submitted:

            if not name.strip():
                st.error(
                    "Please enter vehicle name."
                )

            elif not registration.strip():
                st.error(
                    "Please enter registration number."
                )

            else:

                success, message = add_vehicle(
                    name.strip(),
                    registration.strip(),
                    manufacturing_year
                )

                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


# =========================================================
# SERVICE HISTORY
# =========================================================

elif page == "🔧 Service History":

    st.markdown(
        '<div class="section-title">'
        '🔧 Service History'
        '</div>',
        unsafe_allow_html=True
    )

    st.write(
        f"Complete service history for "
        f"**{selected_vehicle['name']}**"
    )

    services = get_services(vehicle_id)

    # Add service

    with st.expander(
        "➕ Add New Service Record",
        expanded=True
    ):

        with st.form("service_form"):

            col1, col2 = st.columns(2)

            with col1:

                service_type = st.selectbox(
                    "Service Type",
                    [
                        "General Service",
                        "Oil Change",
                        "Brake Service",
                        "Tyre Replacement",
                        "Battery Replacement",
                        "AC Service",
                        "Engine Repair",
                        "Wheel Alignment",
                        "Insurance",
                        "Other"
                    ]
                )

                service_date = st.date_input(
                    "Service Date",
                    value=date.today()
                )

                odometer = st.number_input(
                    "Odometer (km)",
                    min_value=0,
                    value=0,
                    step=100
                )

            with col2:

                amount = st.number_input(
                    "Amount (₹)",
                    min_value=0.0,
                    value=0.0,
                    step=100.0
                )

                workshop = st.text_input(
                    "Workshop / Service Center",
                    placeholder="Example: Sri Sai Motors"
                )

                next_service = st.date_input(
                    "Next Service Due",
                    value=date.today() + timedelta(days=180)
                )

            notes = st.text_area(
                "Notes",
                placeholder=(
                    "Example: Engine oil replaced, "
                    "oil filter changed..."
                )
            )

            submit_service = st.form_submit_button(
                "💾 Save Service Record",
                use_container_width=True
            )

            if submit_service:

                add_service(
                    vehicle_id,
                    service_type,
                    service_date.isoformat(),
                    odometer,
                    amount,
                    workshop,
                    notes,
                    next_service.isoformat()
                )

                st.success(
                    "Service record saved successfully!"
                )

                st.rerun()

    st.markdown("---")

    # Display history

    if services:

        st.subheader(
            f"📋 {len(services)} Service Record(s)"
        )

        for service in services:

            with st.container(border=True):

                c1, c2, c3 = st.columns([2, 2, 1])

                with c1:

                    st.subheader(
                        f"🔧 {service['service_type']}"
                    )

                    st.write(
                        f"📅 {service['service_date']}"
                    )

                    if service["workshop"]:
                        st.write(
                            f"🏪 {service['workshop']}"
                        )

                with c2:

                    st.write(
                        f"💰 **₹{float(service['amount'] or 0):,.2f}**"
                    )

                    st.write(
                        f"🚗 Odometer: "
                        f"{service['odometer']:,} km"
                    )

                    if service["next_service_date"]:
                        st.write(
                            f"⏰ Next: "
                            f"{service['next_service_date']}"
                        )

                with c3:

                    if st.button(
                        "🗑️ Delete",
                        key=f"delete_service_{service['id']}"
                    ):

                        delete_service(
                            service["id"]
                        )

                        st.success(
                            "Service deleted."
                        )

                        st.rerun()

                if service["notes"]:

                    st.caption(
                        f"📝 {service['notes']}"
                    )

    else:

        st.info(
            "No service records yet."
        )


# =========================================================
# DOCUMENTS
# =========================================================

elif page == "📄 Documents":

    st.markdown(
        '<div class="section-title">'
        '📄 Documents'
        '</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Upload and manage invoices, insurance papers, "
        "service bills and other vehicle documents."
    )

    with st.expander(
        "➕ Upload New Document",
        expanded=True
    ):

        document_type = st.selectbox(
            "Document Type",
            [
                "Service Invoice",
                "Insurance",
                "RC",
                "PUC",
                "Warranty",
                "Other"
            ]
        )

        uploaded_file = st.file_uploader(
            "Choose a file",
            type=[
                "pdf",
                "png",
                "jpg",
                "jpeg",
                "webp",
                "txt"
            ]
        )

        if uploaded_file:

            st.write(
                f"Selected: **{uploaded_file.name}**"
            )

            if st.button(
                "💾 Save Document",
                use_container_width=True
            ):

                safe_name = (
                    uploaded_file.name
                    .replace(" ", "_")
                    .replace("/", "_")
                    .replace("\\", "_")
                )

                timestamp = datetime.now().strftime(
                    "%Y%m%d%H%M%S"
                )

                filename = (
                    f"{vehicle_id}_{timestamp}_{safe_name}"
                )

                filepath = os.path.join(
                    UPLOAD_FOLDER,
                    filename
                )

                with open(filepath, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                add_document(
                    vehicle_id,
                    uploaded_file.name,
                    filepath,
                    document_type
                )

                st.success(
                    "Document uploaded successfully!"
                )

                st.rerun()

    st.markdown("---")

    documents = get_documents(vehicle_id)

    if documents:

        st.subheader(
            f"📁 {len(documents)} Document(s)"
        )

        for doc in documents:

            with st.container(border=True):

                c1, c2, c3 = st.columns(
                    [3, 2, 1]
                )

                with c1:

                    st.subheader(
                        f"📄 {doc['filename']}"
                    )

                    st.write(
                        f"Type: "
                        f"{doc['document_type'] or 'Document'}"
                    )

                    st.caption(
                        f"Uploaded: "
                        f"{doc['uploaded_at'][:10]}"
                    )

                with c2:

                    if os.path.exists(
                        doc["filepath"]
                    ):

                        with open(
                            doc["filepath"],
                            "rb"
                        ) as f:

                            file_data = f.read()

                        st.download_button(
                            "⬇️ Download",
                            data=file_data,
                            file_name=doc["filename"],
                            key=f"download_{doc['id']}",
                            use_container_width=True
                        )

                with c3:

                    if st.button(
                        "🗑️ Delete",
                        key=f"delete_doc_{doc['id']}"
                    ):

                        delete_document(
                            doc["id"]
                        )

                        st.success(
                            "Document deleted."
                        )

                        st.rerun()

                # Preview

                if os.path.exists(
                    doc["filepath"]
                ):

                    ext = os.path.splitext(
                        doc["filename"]
                    )[1].lower()

                    with st.expander(
                        "👁️ Preview"
                    ):

                        if ext == ".pdf":

                            import base64

                            with open(
                                doc["filepath"],
                                "rb"
                            ) as f:

                                pdf_data = base64.b64encode(
                                    f.read()
                                ).decode("utf-8")

                            pdf_display = f"""
                            <iframe
                                src="data:application/pdf;base64,
                                {pdf_data}"
                                width="100%"
                                height="700"
                                type="application/pdf">
                            </iframe>
                            """

                            st.markdown(
                                pdf_display,
                                unsafe_allow_html=True
                            )

                        elif ext in [
                            ".png",
                            ".jpg",
                            ".jpeg",
                            ".webp"
                        ]:

                            st.image(
                                doc["filepath"],
                                use_container_width=True
                            )

                        elif ext == ".txt":

                            try:

                                with open(
                                    doc["filepath"],
                                    "r",
                                    encoding="utf-8"
                                ) as f:

                                    st.text(
                                        f.read()
                                    )

                            except:

                                st.warning(
                                    "Unable to preview this file."
                                )

                        else:

                            st.info(
                                "Preview is not available "
                                "for this file type. "
                                "Use Download instead."
                            )

    else:

        st.info(
            "No documents uploaded yet."
        )


# =========================================================
# ANALYTICS
# =========================================================

elif page == "📊 Analytics":

    st.markdown(
        '<div class="section-title">'
        '📊 Service Cost Analytics'
        '</div>',
        unsafe_allow_html=True
    )

    df = service_dataframe(vehicle_id)

    if df.empty:

        st.info(
            "Add service records to see analytics."
        )

    else:

        total = df["Amount"].sum()

        average = df["Amount"].mean()

        highest = df["Amount"].max()

        service_count = len(df)

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "💰 Total Spent",
                f"₹{total:,.2f}"
            )

        with c2:
            st.metric(
                "📊 Average Service Cost",
                f"₹{average:,.2f}"
            )

        with c3:
            st.metric(
                "💸 Highest Service",
                f"₹{highest:,.2f}"
            )

        with c4:
            st.metric(
                "🔧 Total Services",
                service_count
            )

        st.markdown("---")

        # Monthly spending

        st.subheader(
            "📅 Monthly Spending"
        )

        monthly = df.copy()

        monthly["Month"] = (
            monthly["Date"]
            .dt.to_period("M")
            .astype(str)
        )

        monthly_data = (
            monthly
            .groupby("Month")["Amount"]
            .sum()
        )

        st.bar_chart(
            monthly_data
        )

        # Yearly spending

        st.subheader(
            "📆 Yearly Spending"
        )

        yearly = df.copy()

        yearly["Year"] = (
            yearly["Date"]
            .dt.year
            .astype(str)
        )

        yearly_data = (
            yearly
            .groupby("Year")["Amount"]
            .sum()
        )

        st.bar_chart(
            yearly_data
        )

        # Service type

        st.subheader(
            "🔧 Spending by Service Type"
        )

        type_data = (
            df
            .groupby("Service")["Amount"]
            .sum()
            .sort_values(ascending=False)
        )

        st.bar_chart(
            type_data
        )

        # Table

        st.subheader(
            "📋 Spending Details"
        )

        display_df = df.copy()

        display_df["Amount"] = display_df[
            "Amount"
        ].apply(
            lambda x: f"₹{x:,.2f}"
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# MAINTENANCE
# =========================================================

elif page == "⏰ Maintenance":

    st.markdown(
        '<div class="section-title">'
        '⏰ Maintenance Reminder'
        '</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Track your next scheduled service."
    )

    services = get_services(vehicle_id)

    if not services:

        st.info(
            "Add a service record first."
        )

    else:

        next_service = get_next_service(
            vehicle_id
        )

        if next_service:

            next_date, service = next_service

            days_left = (
                next_date - date.today()
            ).days

            if days_left < 0:

                st.error(
                    f"🚨 Service overdue by "
                    f"{abs(days_left)} day(s)."
                )

            elif days_left <= 30:

                st.warning(
                    f"⚠️ Service due in "
                    f"{days_left} day(s)."
                )

            else:

                st.success(
                    f"✅ Next service is in "
                    f"{days_left} day(s)."
                )

            st.markdown(f"""
            <div class="card">
                <h2>🔧 {service["service_type"]}</h2>
                <p>
                    <b>Due Date:</b>
                    {next_date.strftime("%d %B %Y")}
                </p>
                <p>
                    <b>Vehicle:</b>
                    {selected_vehicle["name"]}
                </p>
                <p>
                    <b>Registration:</b>
                    {selected_vehicle["registration"]}
                </p>
            </div>
            """, unsafe_allow_html=True)

        else:

            st.info(
                "No upcoming service date has been "
                "recorded."
            )

        st.markdown("---")

        st.subheader(
            "📋 Service Schedule"
        )

        schedule = []

        for service in services:

            schedule.append({
                "Service":
                    service["service_type"],
                "Service Date":
                    service["service_date"],
                "Next Due":
                    service["next_service_date"]
                    or "Not set",
                "Amount":
                    f"₹{float(service['amount'] or 0):,.2f}"
            })

        st.dataframe(
            pd.DataFrame(schedule),
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# AI ASSISTANT
# =========================================================

elif page == "🤖 AI Assistant":

    st.markdown(
        '<div class="section-title">'
        '🤖 AI Maintenance Assistant'
        '</div>',
        unsafe_allow_html=True
    )

    st.write(
        "AutoHistory analyzes your recorded service "
        "history and provides maintenance suggestions."
    )

    recommendations = maintenance_recommendations(
        vehicle_id
    )

    for icon, title, message in recommendations:

        st.markdown(f"""
        <div class="ai-box">
            <h3>{icon} {title}</h3>
            <p>{message}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader(
        "📊 Vehicle Health Snapshot"
    )

    services = get_services(vehicle_id)

    total = total_spending(vehicle_id)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Service Records",
            len(services)
        )

    with c2:
        st.metric(
            "Total Maintenance Cost",
            f"₹{total:,.0f}"
        )

    with c3:

        if services:
            last_date = services[0]["service_date"]
            st.metric(
                "Last Recorded Service",
                last_date
            )
        else:
            st.metric(
                "Last Recorded Service",
                "None"
            )

    st.info(
        "💡 These recommendations are based on the "
        "service information entered into AutoHistory. "
        "They are general maintenance suggestions and "
        "not a substitute for professional inspection."
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.markdown("""
<div class="footer">
    🚘 <b>AutoHistory</b> |
    Digital Vehicle Service Passport
    <br>
    Built with Python + Streamlit + SQLite
</div>
""", unsafe_allow_html=True)