import streamlit as st 
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pyzbar.pyzbar import decode
import cv2
import numpy as np

SPREADSHEET_ID = '1fuCMvS_fob8at2RrgESGTYnjIyJL5HCm1Rs-0ZZ_SIw'
WORKSHEET_NAME = 'Main'

# Connect to Google Sheets API
def get_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    return sheet

# Fetch user details from Google Sheets by QR Code ID
def fetch_user_details(sheet, qr_id):
    users = sheet.get_all_records()
    for idx, user in enumerate(users, start=2):
        if user['ID'] == qr_id:
            user['Row'] = idx
            return user
    return None

# Mark the user as entered with the current time
def mark_entry(sheet, user_row):
    current_time = datetime.now().strftime("%I:%M %p, %d %b")
    sheet.update_cell(user_row, 9, current_time)  # Assuming Entry time is in column 9

# QR code scanner using webcam
def scan_qr_code():
    cap = cv2.VideoCapture(0)
    
    # Check if the camera opened successfully
    if not cap.isOpened():
        st.error("Error: Could not open camera.")
        return None

    qr_code_data = None
    placeholder = st.empty()
    
    while cap.isOpened() and not st.session_state.stop_scanning:
        ret, frame = cap.read()
        if not ret:
            st.error("Failed to capture video.")
            break
        
        # Detect QR Code
        for barcode in decode(frame):
            qr_code_data = barcode.data.decode("utf-8")
            points = np.array([barcode.polygon], np.int32)
            points = points.reshape((-1, 1, 2))
            cv2.polylines(frame, [points], True, (0, 255, 0), 3)
            rect = barcode.rect
            cv2.putText(frame, qr_code_data, (rect[0], rect[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        # Display the frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        placeholder.image(frame_rgb, channels="RGB", use_column_width=True)
        
        if qr_code_data:
            break

    cap.release()
    cv2.destroyAllWindows()
    return qr_code_data

# Streamlit UI
def main():
    st.title("Event QR Scanner")
    
    # Initialize session state variables
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "scanning" not in st.session_state:
        st.session_state.scanning = False
    if "stop_scanning" not in st.session_state:
        st.session_state.stop_scanning = False
    
    if not st.session_state.logged_in:
        # Login screen
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username == "admin" and password == "admin123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials")
    else:
        if not st.session_state.scanning:
            # Show 'Start QR Scanner' button if not scanning
            if st.button("Start QR Scanner"):
                st.session_state.scanning = True
                st.session_state.stop_scanning = False
                st.rerun()  # To refresh and hide this button
        else:
            # Show 'Stop Scanning' button if scanning
            if st.button("Stop Scanning"):
                st.session_state.stop_scanning = True
                st.session_state.scanning = False
                st.rerun()  # To refresh and hide this button

        if st.session_state.scanning and not st.session_state.stop_scanning:
            qr_id = scan_qr_code()

            if qr_id:
                st.session_state.qr_id = qr_id
                st.success(f"QR Code Detected: {qr_id}")
                
                # Authenticate and access Google Sheets
                sheet = get_sheet()
                
                # Fetch user details
                user_details = fetch_user_details(sheet, qr_id)
                
                if user_details:
                    st.markdown(f"### Name: **{user_details['Name']}**")
                    st.markdown(f"### Registration: **{user_details['Registration']}**")
                    
                    # Check for existing entry
                    entry_time = sheet.cell(user_details['Row'], 9).value  # Assuming Entry time is in column 9
                    if entry_time:
                        st.warning(f"Already scanned at {entry_time}")
                    else:
                        # Mark the entry
                        mark_entry(sheet, user_details['Row'])
                        st.success(f"Entry Marked!")
                else:
                    st.error("No Entry Found! 404")

                st.button("Scan Again", on_click=lambda: st.session_state.update({"scanning": True, "stop_scanning": False}))

                # Reset scanning state
                st.session_state.scanning = False

if __name__ == "__main__":
    main()