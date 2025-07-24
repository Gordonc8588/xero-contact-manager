"""
Xero Contact Manager - Streamlit Interface (Minimalist Version)
==========================================

This module provides a Streamlit web interface for creating new property contacts
in Xero by duplicating existing contacts with modifications.

Migration from tkinter GUI to Streamlit for better multi-module workflow.
"""

import streamlit as st
import time
from typing import Optional, Dict, Any, List
import json
from datetime import date, datetime

# Import our existing modules (keep backend logic unchanged)
from contact_manager import XeroContactManager
from constants import CONTACT_CODES, validate_account_number, parse_account_number
from invoice_manager import (
    XeroInvoiceManager, 
    search_invoices_for_reassignment, 
    reassign_selected_invoices,
    search_repeating_invoices_for_contact,
    reassign_repeating_invoice_template_for_contact
)
from previous_contact_manager import (
    get_previous_contact_balance,
    handle_previous_contact_after_reassignment
)


# Authentication function
def check_password():
    if "password_authenticated" not in st.session_state:
        st.session_state.password_authenticated = False
    
    if not st.session_state.password_authenticated:
        st.title("🔒 Xero Property Manager")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if password == st.secrets["APP_PASSWORD"]:
                st.session_state.password_authenticated = True
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Incorrect password")
        
        st.stop()
    
    return True


# Configure Streamlit page
st.set_page_config(
    page_title="Xero Contact Manager",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state variables
if 'contact_manager' not in st.session_state:
    st.session_state.contact_manager = None
if 'password_authenticated' not in st.session_state:
    st.session_state.password_authenticated = False
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'existing_contact' not in st.session_state:
    st.session_state.existing_contact = None
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False
if 'new_contact' not in st.session_state:
    st.session_state.new_contact = None
if 'found_invoices' not in st.session_state:
    st.session_state.found_invoices = []
if 'selected_invoices' not in st.session_state:
    st.session_state.selected_invoices = []
if 'invoice_search_performed' not in st.session_state:
    st.session_state.invoice_search_performed = False
if 'found_repeating_templates' not in st.session_state:
    st.session_state.found_repeating_templates = []
if 'template_search_performed' not in st.session_state:
    st.session_state.template_search_performed = False
if 'previous_contact_balance' not in st.session_state:
    st.session_state.previous_contact_balance = None
if 'previous_contact_processed' not in st.session_state:
    st.session_state.previous_contact_processed = False

def initialize_contact_manager():
    """Initialize and authenticate contact manager."""
    if st.session_state.contact_manager is None:
        try:
            st.session_state.contact_manager = XeroContactManager()
            return True
        except Exception as e:
            st.error(f"Failed to initialize contact manager: {str(e)}")
            return False
    return True

def authenticate_xero():
    """Authenticate with Xero API."""
    if not st.session_state.authenticated:
        if st.session_state.contact_manager is None:
            if not initialize_contact_manager():
                return False
        
        try:
            with st.spinner("Authenticating with Xero..."):
                success = st.session_state.contact_manager.authenticate()
                if success:
                    st.session_state.authenticated = True
                    st.success("✅ Successfully authenticated with Xero!")
                    return True
                else:
                    st.error("❌ Failed to authenticate with Xero")
                    return False
        except Exception as e:
            st.error(f"Authentication error: {str(e)}")
            return False
    return True

def search_contact(account_number: str):
    """Search for existing contact."""
    if not st.session_state.authenticated:
        if not authenticate_xero():
            return None
    
    try:
        with st.spinner(f"Searching for contact: {account_number}"):
            contact = st.session_state.contact_manager.search_contact_by_account_number(account_number)
            st.session_state.existing_contact = contact
            st.session_state.search_performed = True
            return contact
    except Exception as e:
        st.error(f"Error searching for contact: {str(e)}")
        return None

def create_new_contact(contact_data: Dict[str, str]):
    """Create new contact with provided data."""
    if not st.session_state.existing_contact:
        st.error("No existing contact found. Please search first.")
        return None
    
    try:
        with st.spinner("Creating new contact..."):
            new_contact = st.session_state.contact_manager.create_new_contact(
                st.session_state.existing_contact, 
                contact_data
            )
            # Store new contact for Module 2
            if new_contact:
                st.session_state.new_contact = new_contact
            return new_contact
    except Exception as e:
        st.error(f"Error creating contact: {str(e)}")
        return None

def display_contact_details(contact: Dict[str, Any], title: str):
    """Display contact details in a minimal way."""
    contact_name = contact.get('Name', 'Unknown Contact')
    st.success(f"**Contact found:** {contact_name}")

def search_invoices_for_old_contact(contact_id: str, move_in_date: date):
    """Search for invoices assigned to old contact after move-in date."""
    if not st.session_state.authenticated:
        if not authenticate_xero():
            return []
    
    try:
        with st.spinner(f"Searching for invoices after {move_in_date.strftime('%d %b %Y')}..."):
            # Use existing authentication from contact_manager
            access_token = st.session_state.contact_manager.access_token
            tenant_id = st.session_state.contact_manager.tenant_id
            
            invoices = search_invoices_for_reassignment(
                contact_id, 
                move_in_date, 
                access_token, 
                tenant_id
            )
            
            st.session_state.found_invoices = invoices
            st.session_state.invoice_search_performed = True
            return invoices
    except Exception as e:
        st.error(f"Error searching for invoices: {str(e)}")
        return []

def reassign_invoices(selected_invoice_ids: List[str], new_contact_id: str):
    """Reassign selected invoices to new contact."""
    try:
        with st.spinner(f"Reassigning {len(selected_invoice_ids)} invoices..."):
            # Use existing authentication from contact_manager
            access_token = st.session_state.contact_manager.access_token
            tenant_id = st.session_state.contact_manager.tenant_id
            
            successful, failed = reassign_selected_invoices(
                selected_invoice_ids,
                new_contact_id,
                access_token,
                tenant_id
            )
            
            return successful, failed
    except Exception as e:
        st.error(f"Error reassigning invoices: {str(e)}")
        return [], selected_invoice_ids

def search_repeating_invoices_for_old_contact(contact_id: str):
    """Search for repeating invoice templates assigned to old contact."""
    if not st.session_state.authenticated:
        if not authenticate_xero():
            return []
    
    try:
        with st.spinner("Searching for repeating invoice templates..."):
            # Use existing authentication from contact_manager
            access_token = st.session_state.contact_manager.access_token
            tenant_id = st.session_state.contact_manager.tenant_id
            
            templates = search_repeating_invoices_for_contact(
                contact_id,
                access_token,
                tenant_id
            )
            
            st.session_state.found_repeating_templates = templates
            st.session_state.template_search_performed = True
            return templates
    except Exception as e:
        st.error(f"Error searching for repeating invoice templates: {str(e)}")
        return []

def reassign_repeating_invoice_template(old_contact_id: str, new_contact_id: str):
    """Reassign repeating invoice template from old to new contact."""
    try:
        with st.spinner("Reassigning repeating invoice template..."):
            # Use existing authentication from contact_manager
            access_token = st.session_state.contact_manager.access_token
            tenant_id = st.session_state.contact_manager.tenant_id
            
            result = reassign_repeating_invoice_template_for_contact(
                old_contact_id,
                new_contact_id,
                access_token,
                tenant_id
            )
            
            return result
    except Exception as e:
        st.error(f"Error reassigning repeating invoice template: {str(e)}")
        return {
            'success': False,
            'error': f"Error during template reassignment: {str(e)}"
        }

def get_previous_contact_balance_info(old_contact_id: str):
    """Get balance information for previous contact."""
    if not st.session_state.authenticated:
        if not authenticate_xero():
            return None
    
    try:
        with st.spinner("Checking previous contact balance..."):
            # Use existing authentication from contact_manager
            access_token = st.session_state.contact_manager.access_token
            tenant_id = st.session_state.contact_manager.tenant_id
            
            balance_info = get_previous_contact_balance(
                old_contact_id,
                access_token,
                tenant_id
            )
            
            return balance_info
    except Exception as e:
        st.error(f"Error getting previous contact balance: {str(e)}")
        return None

def handle_previous_contact_workflow(old_contact_id: str):
    """Handle the complete previous contact workflow."""
    try:
        with st.spinner("Processing previous contact..."):
            # Use existing authentication from contact_manager
            access_token = st.session_state.contact_manager.access_token
            tenant_id = st.session_state.contact_manager.tenant_id
            
            result = handle_previous_contact_after_reassignment(
                old_contact_id,
                access_token,
                tenant_id
            )
            
            return result
    except Exception as e:
        st.error(f"Error handling previous contact: {str(e)}")
        return {
            'success': False,
            'error': f"Error during previous contact handling: {str(e)}"
        }

# Main Streamlit App
def main():
    # Minimalist header
    st.title("🏢 Xero Property Contact Manager")
    
    # Status indicator
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        pass
    with col2:
        if st.session_state.authenticated:
            st.success("🟢 Connected")
        else:
            st.warning("🟡 Not connected")
    with col3:
        if st.button("🔄 Reset", type="secondary"):
            keys_to_clear = ['existing_contact', 'search_performed', 'new_contact', 'found_invoices', 
                           'selected_invoices', 'found_repeating_templates', 'previous_contact_balance', 'previous_contact_processed']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    st.markdown("---")
    
    # ============================================================================
    # SECTION 1: Search Existing Contact (Always visible, compact)
    # ============================================================================
    
    col1, col2 = st.columns([3, 1])
    with col1:
        account_number = st.text_input("Account Number", placeholder="e.g., ANP001042 or ANP001042/3B")
    with col2:
        search_clicked = st.button("🔍 Search", type="primary")
    
    # Handle search
    if search_clicked and account_number:
        account_number = account_number.strip().upper()
        if len(account_number) != 8 and not validate_account_number(account_number):
            st.error("❌ Invalid account number format")
        else:
            contact = search_contact(account_number)
            if contact:
                display_contact_details(contact, "Found Contact Details")
            else:
                st.error("❌ No contact found")
    elif search_clicked and not account_number:
        st.error("❌ Please enter an account number")
    
    # ============================================================================
    # SECTION 2: New Contact Details (only show if contact found)
    # ============================================================================
    
    if st.session_state.existing_contact:
        st.markdown("---")
        
        # Compact form layout
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            contact_codes = list(CONTACT_CODES.keys())
            contact_codes.sort()
            selected_code = st.selectbox("Contact Code *", options=contact_codes, index=None, placeholder="Choose...")
        
        with col2:
            first_name = st.text_input("First Name *", value="Occupier", placeholder="Enter first name")
        
        with col3:
            last_name = st.text_input("Last Name", placeholder="Enter last name")
        
        with col4:
            email = st.text_input("Email", placeholder="Enter email")
        
        # Validation and create button
        can_create = bool(selected_code and first_name.strip())
        
        if can_create:
            if st.button("🆕 Create New Contact", type="primary"):
                new_contact_data = {
                    'contact_code': selected_code,
                    'first_name': first_name.strip(),
                    'last_name': last_name.strip(),
                    'email': email.strip()
                }
                
                new_contact = create_new_contact(new_contact_data)
                if new_contact:
                    st.success(f"✅ Created: {new_contact.get('Name', 'Unknown')}")
    
    # ============================================================================
    # SECTION 3: Invoice Reassignment (only show if new contact created)
    # ============================================================================
    
    if st.session_state.new_contact and st.session_state.existing_contact:
        st.markdown("---")
        
        # Compact invoice search
        col1, col2 = st.columns([2, 1])
        with col1:
            move_in_date = st.date_input("Move-in Date", value=date.today())
        with col2:
            if st.button("🔍 Find Invoices", type="primary"):
                old_contact_id = st.session_state.existing_contact.get('ContactID')
                if old_contact_id:
                    invoices = search_invoices_for_old_contact(old_contact_id, move_in_date)
                    if invoices:
                        st.success(f"✅ Found {len(invoices)} invoices")
                    else:
                        st.info("No invoices found")
        
        # Display invoices compactly
        if st.session_state.found_invoices:
            selected_for_reassignment = []
            
            # Compact invoice list
            for i, invoice in enumerate(st.session_state.found_invoices):
                invoice_id = invoice.get('InvoiceID', '')
                invoice_number = invoice.get('InvoiceNumber', 'N/A')
                total = invoice.get('Total', 0)
                status = invoice.get('Status', 'N/A')
                
                col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
                
                with col1:
                    is_selected = st.checkbox("", key=f"inv_{i}", value=invoice_id in st.session_state.selected_invoices)
                    if is_selected:
                        selected_for_reassignment.append(invoice_id)
                
                with col2:
                    st.write(f"**{invoice_number}**")
                
                with col3:
                    st.write(f"${float(total):.2f}")
                
                with col4:
                    st.write(f"{status}")
            
            st.session_state.selected_invoices = selected_for_reassignment
            
            # Reassign button
            if selected_for_reassignment:
                if st.button(f"🔄 Reassign {len(selected_for_reassignment)} Invoices", type="primary"):
                    new_contact_id = st.session_state.new_contact.get('ContactID')
                    if new_contact_id:
                        successful, failed = reassign_invoices(selected_for_reassignment, new_contact_id)
                        if successful:
                            st.success(f"✅ Reassigned {len(successful)} invoices")
                            st.session_state.selected_invoices = []
    
    # ============================================================================
    # SECTION 4: Repeating Invoice Template (compact)
    # ============================================================================
    
    if st.session_state.new_contact and st.session_state.existing_contact:
        st.markdown("---")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write("**Repeating Invoice Template:**")
        with col2:
            if st.button("🔍 Find Template", type="primary"):
                old_contact_id = st.session_state.existing_contact.get('ContactID')
                if old_contact_id:
                    templates = search_repeating_invoices_for_old_contact(old_contact_id)
                    if templates:
                        st.success(f"✅ Found template")
                    else:
                        st.info("No template found")
        
        # Handle template reassignment
        if st.session_state.found_repeating_templates:
            template = st.session_state.found_repeating_templates[0]
            reference = template.get('Reference', 'N/A')
            st.write(f"Template: {reference}")
            
            if st.button("🔄 Reassign Template", type="primary"):
                old_contact_id = st.session_state.existing_contact.get('ContactID')
                new_contact_id = st.session_state.new_contact.get('ContactID')
                if old_contact_id and new_contact_id:
                    result = reassign_repeating_invoice_template(old_contact_id, new_contact_id)
                    if result.get('success'):
                        st.success("✅ Template reassigned")
                        st.session_state.found_repeating_templates = []
    
    # ============================================================================
    # SECTION 5: Previous Contact Management (compact)
    # ============================================================================
    
    if st.session_state.new_contact and st.session_state.existing_contact and not st.session_state.previous_contact_processed:
        st.markdown("---")
        
        # Balance check
        if not st.session_state.previous_contact_balance:
            col1, col2 = st.columns([2, 1])
            with col1:
                old_contact_name = st.session_state.existing_contact.get('Name', 'Unknown')
                st.write(f"**Previous Contact:** {old_contact_name}")
            with col2:
                if st.button("💰 Check Balance", type="primary"):
                    old_contact_id = st.session_state.existing_contact.get('ContactID')
                    if old_contact_id:
                        balance_info = get_previous_contact_balance_info(old_contact_id)
                        if balance_info:
                            st.session_state.previous_contact_balance = balance_info
                            st.rerun()
        
        # Handle previous contact
        if st.session_state.previous_contact_balance:
            balance_info = st.session_state.previous_contact_balance
            outstanding = balance_info['outstanding']
            has_balance = balance_info['has_balance']
            
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                status_text = f"Balance: ${outstanding:.2f} - {'Keep Active' if has_balance else 'Set Inactive'}"
                st.write(status_text)
            with col2:
                st.write("Action: /P code")
            with col3:
                if st.button("🔄 Handle", type="primary"):
                    old_contact_id = st.session_state.existing_contact.get('ContactID')
                    result = handle_previous_contact_workflow(old_contact_id)
                    if result.get('success'):
                        st.success("✅ Previous contact handled")
                        st.session_state.previous_contact_processed = True
    
    # Completion message
    if st.session_state.previous_contact_processed:
        st.markdown("---")
        st.success("🎉 **Workflow Complete!** All steps finished successfully.")

if __name__ == "__main__":
    if check_password():
        main()
