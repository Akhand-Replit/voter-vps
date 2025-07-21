import streamlit as st
import pandas as pd
from utils.database import Database
from utils.styling import apply_custom_styling
import logging

logger = logging.getLogger(__name__)
apply_custom_styling()

def editable_search_page():
    """
    A search page where the results are displayed in editable cards,
    allowing direct modification of record data and event assignments.
    """
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.warning("অনুগ্রহ করে প্রথমে লগইন করুন")
        return

    st.title("✏️ তথ্য খুঁজুন এবং সম্পাদনা করুন")
    st.markdown("এখানে আপনি তথ্য অনুসন্ধান করতে এবং সরাসরি ফলাফল সম্পাদনা করতে পারেন।")

    db = Database()

    # --- Search UI ---
    with st.container(border=True):
        st.subheader("অনুসন্ধান ফিল্টার")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("নাম")
            fathers_name = st.text_input("পিতার নাম")
            phone_number = st.text_input("ফোন নম্বর")
        with col2:
            voter_no = st.text_input("ভোটার নং")
            address = st.text_input("ঠিকানা")
            si_number = st.text_input("ক্রমিক নং")

    if st.button("🔍 অনুসন্ধান করুন", type="primary", use_container_width=True):
        search_criteria = {
            'নাম': name,
            'পিতার_নাম': fathers_name,
            'phone_number': phone_number,
            'ভোটার_নং': voter_no,
            'ঠিকানা': address,
            'ক্রমিক_নং': si_number,
        }
        # Remove empty criteria to search only with provided values
        search_criteria = {k: v for k, v in search_criteria.items() if v}

        if not search_criteria:
            st.warning("অনুসন্ধানের জন্য অন্তত একটি ফিল্টার পূরণ করুন।")
            return

        try:
            with st.spinner("অনুসন্ধান করা হচ্ছে..."):
                results = db.search_records_advanced(search_criteria)
            
            st.session_state.search_results = results
            if not results:
                st.info("আপনার অনুসন্ধানের সাথে মেলে এমন কোনো ফলাফল পাওয়া যায়নি।")

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            st.error(f"অনুসন্ধানে সমস্যা হয়েছে: {str(e)}")

    # --- Display Search Results ---
    if 'search_results' in st.session_state and st.session_state.search_results:
        st.markdown("---")
        st.subheader(f"অনুসন্ধানের ফলাফল ({len(st.session_state.search_results)} টি)")

        all_events = db.get_all_events()
        event_map = {event['name']: event['id'] for event in all_events}

        for record in st.session_state.search_results:
            with st.expander(f"**{record['নাম']}** (ক্রমিক নং: {record['ক্রমিক_নং']})"):
                
                # Create a unique key for each form to isolate its state
                form_key = f"form_{record['id']}"
                with st.form(key=form_key):
                    st.markdown(f"#### রেকর্ড আইডি: {record['id']}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        # Editable fields
                        edited_name = st.text_input("নাম", value=record.get('নাম', ''), key=f"name_{record['id']}")
                        edited_father = st.text_input("পিতার নাম", value=record.get('পিতার_নাম', ''), key=f"father_{record['id']}")
                        edited_mother = st.text_input("মাতার নাম", value=record.get('মাতার_নাম', ''), key=f"mother_{record['id']}")
                        edited_voter_no = st.text_input("ভোটার নং", value=record.get('ভোটার_নং', ''), key=f"voter_{record['id']}")
                        edited_phone = st.text_input("ফোন নম্বর", value=record.get('phone_number', ''), key=f"phone_{record['id']}")
                        edited_fb = st.text_input("ফেসবুক লিঙ্ক", value=record.get('facebook_link', ''), key=f"fb_{record['id']}")

                    with c2:
                        edited_si = st.text_input("ক্রমিক নং", value=record.get('ক্রমিক_নং', ''), key=f"si_{record['id']}")
                        edited_occupation = st.text_input("পেশা", value=record.get('পেশা', ''), key=f"occupation_{record['id']}")
                        edited_dob = st.text_input("জন্ম তারিখ", value=record.get('জন্ম_তারিখ', ''), key=f"dob_{record['id']}")
                        edited_address = st.text_area("ঠিকানা", value=record.get('ঠিকানা', ''), key=f"address_{record['id']}")
                        edited_photo = st.text_input("ছবির লিঙ্ক", value=record.get('photo_link', ''), key=f"photo_{record['id']}")

                    edited_description = st.text_area("বিবরণ", value=record.get('description', ''), key=f"desc_{record['id']}")
                    
                    st.markdown("---")
                    
                    # Relationship and Event assignment
                    rel_col, event_col = st.columns(2)
                    with rel_col:
                        edited_relationship = st.selectbox(
                            "সম্পর্কের ধরণ",
                            options=['Regular', 'Friend', 'Enemy', 'Connected'],
                            index=['Regular', 'Friend', 'Enemy', 'Connected'].index(record.get('relationship_status', 'Regular')),
                            key=f"rel_{record['id']}"
                        )
                    with event_col:
                        assigned_events = db.get_events_for_record(record['id'])
                        selected_events = st.multiselect(
                            "ইভেন্ট নির্ধারণ করুন",
                            options=event_map.keys(),
                            default=assigned_events,
                            key=f"events_{record['id']}"
                        )

                    # Submit button for the form
                    if st.form_submit_button("💾 পরিবর্তন সংরক্ষণ করুন", type="primary"):
                        try:
                            # 1. Update Record Details
                            updated_data = {
                                'ক্রমিক_নং': edited_si, 'নাম': edited_name, 'ভোটার_নং': edited_voter_no,
                                'পিতার_নাম': edited_father, 'মাতার_নাম': edited_mother, 'পেশা': edited_occupation,
                                'ঠিকানা': edited_address, 'জন্ম_তারিখ': edited_dob, 'phone_number': edited_phone,
                                'facebook_link': edited_fb, 'photo_link': edited_photo, 'description': edited_description,
                                'relationship_status': edited_relationship
                            }
                            db.update_record(record['id'], updated_data)

                            # 2. Update Event Assignments
                            selected_event_ids = [event_map[name] for name in selected_events]
                            db.assign_events_to_record(record['id'], selected_event_ids)

                            st.success(f"রেকর্ড '{record['নাম']}' সফলভাবে আপডেট করা হয়েছে।")
                            # Clear results to allow a new search
                            st.session_state.search_results = []
                            st.rerun()

                        except Exception as e:
                            logger.error(f"Update failed for record {record['id']}: {e}")
                            st.error("তথ্য আপডেট করার সময় একটি সমস্যা হয়েছে।")

if __name__ == "__main__":
    editable_search_page()
