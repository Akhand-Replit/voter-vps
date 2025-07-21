import streamlit as st
import pandas as pd
import numpy as np
from utils.database import Database
from utils.styling import apply_custom_styling
import logging

logger = logging.getLogger(__name__)
apply_custom_styling()

def all_data_page():
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.warning("অনুগ্রহ করে প্রথমে লগইন করুন")
        return

    st.title("📁 সব তথ্য")

    db = Database()
    batches = db.get_all_batches()

    if not batches:
        st.info("কোন ডাটা পাওয়া যায়নি")
        return

    # --- Session State Initialization ---
    if 'confirm_delete_all' not in st.session_state:
        st.session_state.confirm_delete_all = False
    if 'confirm_delete_batch' not in st.session_state:
        st.session_state.confirm_delete_batch = None
    if 'confirm_delete_file' not in st.session_state:
        st.session_state.confirm_delete_file = None

    # --- Header and Deletion Section ---
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("সব ডাটা মুছুন", type="secondary"):
            st.session_state.confirm_delete_all = True

    if st.session_state.confirm_delete_all:
        st.warning("⚠️ সতর্কতা! আপনি কি নিশ্চিত যে আপনি সমস্ত ডেটা মুছে ফেলতে চান? এই কাজটি অপরিবর্তনীয়!")
        confirm_col1, confirm_col2 = st.columns(2)
        with confirm_col1:
            if st.button("হ্যাঁ, সব মুছে ফেলুন", type="primary", use_container_width=True):
                db.clear_all_data()
                st.success("✅ সমস্ত ডেটা সফলভাবে মুছে ফেলা হয়েছে")
                st.session_state.confirm_delete_all = False
                st.rerun()
        with confirm_col2:
            if st.button("না, বাতিল করুন", type="secondary", use_container_width=True):
                st.session_state.confirm_delete_all = False
                st.rerun()

    # --- Batch and File Selection ---
    with col1:
        selected_batch_name = st.selectbox(
            "ব্যাচ নির্বাচন করুন",
            options=[batch['name'] for batch in batches],
            format_func=lambda x: f"ব্যাচ: {x}"
        )
    
    selected_batch_id = next(b['id'] for b in batches if b['name'] == selected_batch_name)
    files = db.get_batch_files(selected_batch_id)

    if not files:
        st.info("এই ব্যাচে কোন ফাইল নেই")
        return
        
    selected_file_name = st.selectbox(
        "ফাইল নির্বাচন করুন",
        options=['সব'] + [file['file_name'] for file in files],
        format_func=lambda x: f"ফাইল: {x}" if x != 'সব' else "সব ফাইল দেখুন"
    )

    # --- Data Display and Editing ---
    if selected_file_name == 'সব':
        records = db.get_batch_records(selected_batch_id)
    else:
        records = db.get_file_records(selected_batch_id, selected_file_name)

    if records:
        df = pd.DataFrame(records)
        st.write(f"মোট রেকর্ড: {len(records)}")

        # Keep original df in session state for comparison
        st.session_state.original_df = df.copy()

        edited_df = st.data_editor(
            df,
            column_config={
                'id': None, 'batch_id': None, 'file_name': None, 'created_at': None, 'batch_name': None,
                'ক্রমিক_নং': st.column_config.TextColumn('ক্রমিক নং', width="small"),
                'নাম': st.column_config.TextColumn('নাম', width="medium"),
                'ভোটার_নং': st.column_config.TextColumn('ভোটার নং', width="medium"),
                'পিতার_নাম': st.column_config.TextColumn('পিতার নাম', width="medium"),
                'মাতার_নাম': st.column_config.TextColumn('মাতার নাম', width="medium"),
                'পেশা': st.column_config.TextColumn('পেশা'),
                'ঠিকানা': st.column_config.TextColumn('ঠিকানা', width="large"),
                'জন্ম_তারিখ': st.column_config.TextColumn('জন্ম তারিখ'),
                'phone_number': st.column_config.TextColumn('ফোন নম্বর'),
                'facebook_link': st.column_config.LinkColumn('ফেসবুক লিঙ্ক'),
                'photo_link': st.column_config.ImageColumn('ছবি', help="ছবির লিঙ্ক দিন"),
                'description': st.column_config.TextColumn('বিবরণ'),
                'relationship_status': st.column_config.SelectboxColumn(
                    'সম্পর্কের ধরণ', options=['Regular', 'Friend', 'Enemy', 'Connected'], required=True
                ),
                'events': st.column_config.ListColumn('ইভেন্টস', help="এই রেকর্ডের জন্য নির্ধারিত ইভেন্ট")
            },
            hide_index=True,
            use_container_width=True,
            key="data_editor"
        )

        if st.button("রেকর্ডের পরিবর্তনগুলি সংরক্ষণ করুন", type="primary"):
            try:
                original_df = st.session_state.original_df
                # Compare only editable columns
                editable_cols = [
                    'ক্রমিক_নং', 'নাম', 'ভোটার_নং', 'পিতার_নাম', 'মাতার_নাম', 'পেশা', 
                    'ঠিকানা', 'জন্ম_তারিখ', 'phone_number', 'facebook_link', 
                    'photo_link', 'description', 'relationship_status'
                ]
                changes = edited_df[editable_cols].compare(original_df[editable_cols])
                
                if not changes.empty:
                    updated_count = 0
                    for idx in changes.index:
                        record_id = int(original_df.loc[idx, 'id'])
                        updated_data = edited_df.loc[idx].to_dict()
                        db.update_record(record_id, updated_data)
                        updated_count += 1
                    st.success(f"{updated_count} টি রেকর্ডের পরিবর্তন সফলভাবে সংরক্ষিত হয়েছে!")
                    st.rerun()
                else:
                    st.info("কোনো পরিবর্তন সনাক্ত করা যায়নি।")
            except Exception as e:
                logger.error(f"Update error: {str(e)}")
                st.error(f"পরিবর্তন সংরক্ষণে সমস্যা হয়েছে: {str(e)}")
    else:
        st.info("কোন রেকর্ড পাওয়া যায়নি")

    # --- Assign Events Section ---
    st.markdown("---")
    st.subheader("👥 রেকর্ডে ইভেন্ট নির্ধারণ করুন")

    if records:
        all_events = db.get_all_events()
        event_map = {event['name']: event['id'] for event in all_events}
        
        # Let user select a record from the displayed list
        record_options = {f"{rec['ক্রমিক_নং']}: {rec['নাম']}": rec['id'] for rec in records}
        selected_record_display = st.selectbox(
            "রেকর্ড নির্বাচন করুন",
            options=record_options.keys()
        )

        if selected_record_display:
            selected_record_id = record_options[selected_record_display]
            
            # Get currently assigned events for the selected record
            assigned_events_names = db.get_events_for_record(selected_record_id)

            # Multiselect for choosing events
            selected_events = st.multiselect(
                "নির্ধারণ করার জন্য ইভেন্ট নির্বাচন করুন",
                options=event_map.keys(),
                default=assigned_events_names
            )

            if st.button("ইভেন্ট আপডেট করুন", type="primary"):
                try:
                    selected_event_ids = [event_map[name] for name in selected_events]
                    db.assign_events_to_record(selected_record_id, selected_event_ids)
                    st.success(f"রেকর্ড '{selected_record_display}' এর জন্য ইভেন্ট সফলভাবে আপডেট করা হয়েছে।")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Event assignment error: {e}")
                    st.error("ইভেন্ট নির্ধারণের সময় একটি সমস্যা হয়েছে।")

if __name__ == "__main__":
    all_data_page()
