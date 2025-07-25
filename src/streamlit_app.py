"""
Xero Contact Manager - Streamlit Interface (Updated with Invoice Splitting)
==========================================

This module provides a Streamlit web interface for creating new property contacts
in Xero by duplicating existing contacts with modifications.

UPDATED: Now includes invoice splitting functionality for occupier transitions.
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
# NEW: Import invoice splitting functions
from invoice_splitter import (
    get_latest_invoice_for_splitting,
    calculate_invoice_split,
    execute_invoice_split
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

# Initialize session state variables (UPDATED: Added invoice splitting variables)
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
if 'contact_validation_result' not in st.session_state:
    st.session_state.contact_validation_result = None
if 'selected_contact_option' not in st.session_state:
    st.session_state.selected_contact_option = None

# NEW: Invoice splitting session state variables
if 'invoice_splitting_mode' not in st.session_state:
    st.session_state.invoice_splitting_mode = False
if 'invoice_to_split' not in st.session_state:
    st.session_state.invoice_to_split = None
if 'split_calculation' not in st.session_state:
    st.session_state.split_calculation = None
if 'split_executed' not in st.session_state:
    st.session_state.split_executed = False
if 'vacate_date' not in st.session_state:
    st.session_state.vacate_date = None
if 'move_in_date' not in st.session_state:
    st.session_state.move_in_date = None

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

def validate_contact_creation(existing_contact, selected_code):
    """Validate contact creation and check for duplicates."""
    if not st.session_state.authenticated:
        if not authenticate_xero():
            return None
    
    try:
        validation_result = st.session_state.contact_manager.validate_contact_before_creation(
            existing_contact, selected_code
        )
        return validation_result
    except Exception as e:
        st.error(f"Error validating contact: {str(e)}")
        return None

def handle_contact_creation_with_option(contact_data: Dict[str, str], selected_option: Dict[str, Any]):
    """Handle contact creation based on selected duplicate resolution option."""
    if not st.session_state.existing_contact:
        st.error("No existing contact found. Please search first.")
        return None
    
    try:
        if selected_option['type'] == 'use_existing':
            # User chose to use existing contact - just return the existing contact data
            existing_contact_id = selected_option['contact_id']
            
            # Fetch full contact details
            with st.spinner("Loading existing contact details..."):
                # We can use the contact data we already have or fetch fresh
                existing_contact_data = {
                    'ContactID': existing_contact_id,
                    'Name': selected_option['contact_name'],
                    'AccountNumber': selected_option['account_number']
                }
                
                st.session_state.new_contact = existing_contact_data
                return existing_contact_data
                
        elif selected_option['type'] == 'create_next':
            # User chose to create next sequential contact
            # Modify the contact data to use the next available account number
            modified_contact_data = contact_data.copy()
            
            # Extract the contact code from the next available account number
            next_account = selected_option['account_number']
            if '/' in next_account:
                contact_code = '/' + next_account.split('/')[-1]
                modified_contact_data['contact_code'] = contact_code
            
            with st.spinner("Creating next sequential contact..."):
                new_contact = st.session_state.contact_manager.create_new_contact(
                    st.session_state.existing_contact, 
                    modified_contact_data
                )
                
                if new_contact:
                    st.session_state.new_contact = new_contact
                return new_contact
        else:
            st.error("Invalid option selected")
            return None
            
    except Exception as e:
        st.error(f"Error handling contact creation: {str(e)}")
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

# NEW: Invoice splitting functions
def get_invoice_for_splitting(old_contact_id: str):
    """Get the latest unpaid invoice for splitting."""
    if not st.session_state.authenticated:
        if not authenticate_xero():
            return None
    
    try:
        with st.spinner("Finding latest unpaid invoice..."):
            # Use existing authentication from contact_manager
            access_token = st.session_state.contact_manager.access_token
            tenant_id = st.session_state.contact_manager.tenant_id
            
            invoice = get_latest_invoice_for_splitting(
                old_contact_id,
                access_token,
                tenant_id
            )
            
            return invoice
    except Exception as e:
        st.error(f"Error getting invoice for splitting: {str(e)}")
        return None

def calculate_split(invoice: Dict[str, Any], contact_data: Dict[str, Any], 
                   vacate_date: date, move_in_date: date):
    """Calculate invoice split between occupiers."""
    if not st.session_state.authenticated:
        if not authenticate_xero():
            return None
    
    try:
        with st.spinner("Calculating invoice split..."):
            # Use existing authentication from contact_manager
            access_token = st.session_state.contact_manager.access_token
            tenant_id = st.session_state.contact_manager.tenant_id
            
            split_result = calculate_invoice_split(
                invoice,
                contact_data,
                vacate_date,
                move_in_date,
                access_token,
                tenant_id
            )
            
            return split_result
    except Exception as e:
        st.error(f"Error calculating split: {str(e)}")
        return {
            'success': False,
            'error': f"Error calculating split: {str(e)}"
        }

def execute_split(invoice: Dict[str, Any], new_contact_id: str, split_calculation: Dict[str, Any]):
    """Execute the invoice split (modify existing + create new)."""
    if not st.session_state.authenticated:
        if not authenticate_xero():
            return None
    
    try:
        with st.spinner("Executing invoice split..."):
            # Use existing authentication from contact_manager
            access_token = st.session_state.contact_manager.access_token
            tenant_id = st.session_state.contact_manager.tenant_id
            
            split_result = execute_invoice_split(
                invoice,
                new_contact_id,
                split_calculation,
                access_token,
                tenant_id
            )
            
            return split_result
    except Exception as e:
        st.error(f"Error executing split: {str(e)}")
        return {
            'success': False,
            'error': f"Error executing split: {str(e)}"
        }

# Main Streamlit App
def main():

    # Add logo at the top
    st.image("src/assets/logo-trasparent-06.png", width=300)

    # Minimalist header
    st.title("🏢 Xero New Occupier Manager")
    
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
            # Updated to include invoice splitting variables
            keys_to_clear = [
                'existing_contact', 'search_performed', 'new_contact', 'found_invoices', 
                'selected_invoices', 'found_repeating_templates', 'previous_contact_balance', 
                'previous_contact_processed', 'contact_validation_result', 'selected_contact_option',
                'invoice_splitting_mode', 'invoice_to_split', 'split_calculation', 'split_executed',
                'vacate_date', 'move_in_date'
            ]
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
        
        # Show contact creation status
        if st.session_state.new_contact:
            st.success(f"✅ Contact created: {st.session_state.new_contact.get('Name', 'Unknown')} ({st.session_state.new_contact.get('AccountNumber', 'N/A')})")
        
        # Real-time validation when contact code is selected (but NOT if contact already created)
        if selected_code and not st.session_state.new_contact:
            if st.session_state.contact_validation_result is None or \
               st.session_state.contact_validation_result.get('contact_code') != selected_code:
                
                # Validate the contact creation
                validation_result = validate_contact_creation(st.session_state.existing_contact, selected_code)
                
                if validation_result:
                    validation_result['contact_code'] = selected_code  # Store which code was validated
                    st.session_state.contact_validation_result = validation_result
                    # Reset option selection when validation changes
                    st.session_state.selected_contact_option = None
                    st.rerun()
        
        # Show validation results (only if no contact created yet)
        if st.session_state.contact_validation_result and not st.session_state.new_contact:
            validation = st.session_state.contact_validation_result
            
            if validation['status'] == 'available':
                st.success(f"✅ {validation['message']}")
                
            elif validation['status'] == 'duplicate_found':
                st.warning(f"⚠️ {validation['message']}")
                
                # Show options for duplicate resolution
                st.markdown("**Choose how to proceed:**")
                
                for i, option in enumerate(validation['options']):
                    option_key = f"option_{i}"
                    
                    if option['type'] == 'use_existing':
                        if st.button(f"📋 Use existing contact: {option['account_number']}", 
                                   key=option_key, use_container_width=True):
                            st.session_state.selected_contact_option = option
                            st.rerun()
                            
                    elif option['type'] == 'create_next':
                        if st.button(f"🆕 Create new contact: {option['account_number']}", 
                                   key=option_key, use_container_width=True):
                            st.session_state.selected_contact_option = option
                            st.rerun()
                            
                    elif option['type'] == 'no_available':
                        st.error("❌ No sequential numbers available - please choose a different contact code")
                
            elif validation['status'] == 'error':
                st.error(f"❌ {validation['message']}")
        
        # Show selected option and create button (only if no contact created yet)
        if st.session_state.selected_contact_option and not st.session_state.new_contact:
            selected_option = st.session_state.selected_contact_option
            
            if selected_option['type'] == 'use_existing':
                st.info(f"📋 **Selected:** Use existing contact {selected_option['account_number']}")
            elif selected_option['type'] == 'create_next':
                st.info(f"🆕 **Selected:** Create new contact {selected_option['account_number']}")
            
            # Validation and create button
            can_create = bool(selected_code and first_name.strip())
            
            if can_create:
                if st.button("✅ Proceed with Selected Option", type="primary"):
                    new_contact_data = {
                        'contact_code': selected_code,
                        'first_name': first_name.strip(),
                        'last_name': last_name.strip(),
                        'email': email.strip()
                    }
                    
                    new_contact = handle_contact_creation_with_option(new_contact_data, selected_option)
                    if new_contact:
                        if selected_option['type'] == 'use_existing':
                            st.success(f"✅ Using existing contact: {new_contact.get('Name', 'Unknown')}")
                        else:
                            st.success(f"✅ Created new contact: {new_contact.get('Name', 'Unknown')}")
                        
                        # Clear validation state for next time
                        st.session_state.contact_validation_result = None
                        st.session_state.selected_contact_option = None
            else:
                missing = []
                if not selected_code:
                    missing.append("Contact Code")
                if not first_name.strip():
                    missing.append("First Name")
                st.warning(f"⚠️ Please provide: {', '.join(missing)}")
        
        elif selected_code and st.session_state.contact_validation_result and \
             st.session_state.contact_validation_result['status'] == 'available' and \
             not st.session_state.new_contact:
            # Normal creation path for available contacts
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
                        
                        # Clear validation state for next time
                        st.session_state.contact_validation_result = None
    
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
                    is_selected = st.checkbox("Select", key=f"inv_{i}", value=invoice_id in st.session_state.selected_invoices, label_visibility="collapsed")
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
    # SECTION 5: Previous Contact Management (UPDATED: Two button options)
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
                        else:
                            st.error("❌ Failed to get balance information")
        
        # UPDATED: Show TWO button options if balance is available
        if st.session_state.previous_contact_balance and not st.session_state.invoice_splitting_mode:
            balance_info = st.session_state.previous_contact_balance
            outstanding = balance_info['outstanding']
            has_balance = balance_info['has_balance']
            
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                status_text = f"Balance: ${outstanding:.2f} - {'Keep Active' if has_balance else 'Set Inactive'}"
                st.write(status_text)
            with col2:
                if st.button("🔄 Handle", type="primary"):
                    old_contact_id = st.session_state.existing_contact.get('ContactID')
                    result = handle_previous_contact_workflow(old_contact_id)
                    
                    if result.get('success') or result.get('added_to_previous_group'):
                        st.success("✅ Previous contact workflow completed successfully!")
                        st.session_state.previous_contact_processed = True
                        st.rerun()
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        st.error(f"❌ Workflow reported failure: {error_msg}")
            
            with col3:
                if st.button("✂️ Split Invoice", type="secondary"):
                    # Start invoice splitting workflow
                    st.session_state.invoice_splitting_mode = True
                    old_contact_id = st.session_state.existing_contact.get('ContactID')
                    
                    # Get latest invoice for splitting
                    invoice = get_invoice_for_splitting(old_contact_id)
                    if invoice:
                        st.session_state.invoice_to_split = invoice
                        st.rerun()
                    else:
                        st.error("❌ No unpaid invoice found for splitting")
    
    # ============================================================================
    # NEW SECTION: Invoice Splitting Workflow
    # ============================================================================
    
    if st.session_state.invoice_splitting_mode and st.session_state.invoice_to_split:
        st.markdown("---")
        st.markdown("## ✂️ **Invoice Splitting Workflow**")
        
        invoice = st.session_state.invoice_to_split
        invoice_number = invoice.get('InvoiceNumber', 'N/A')
        invoice_total = float(invoice.get('Total', 0))
        amount_due = float(invoice.get('AmountDue', 0))
        
        # Display invoice being split
        st.info(f"**Splitting Invoice:** {invoice_number} - Total: £{invoice_total:.2f} (Due: £{amount_due:.2f})")
        
        # Date input section
        if not st.session_state.split_calculation:
            col1, col2 = st.columns(2)
            
            with col1:
                vacate_date = st.date_input("Previous Occupier Vacate Date:", 
                                          value=st.session_state.vacate_date or date.today(),
                                          key="vacate_date_input")
                st.session_state.vacate_date = vacate_date
            
            with col2:
                move_in_date = st.date_input("New Occupier Move-in Date:", 
                                           value=st.session_state.move_in_date or date.today(),
                                           key="move_in_date_input")
                st.session_state.move_in_date = move_in_date
            
            # Calculate split button
            if st.button("🧮 Calculate Split", type="primary"):
                if vacate_date and move_in_date:
                    contact_data = st.session_state.existing_contact
                    split_result = calculate_split(invoice, contact_data, vacate_date, move_in_date)
                    
                    if split_result and split_result.get('success'):
                        st.session_state.split_calculation = split_result
                        st.rerun()
                    else:
                        error_msg = split_result.get('error', 'Unknown error') if split_result else 'Calculation failed'
                        st.error(f"❌ Split calculation failed: {error_msg}")
                else:
                    st.error("❌ Please enter both dates")
        
        # Display calculation results
        if st.session_state.split_calculation and not st.session_state.split_executed:
            split_calc = st.session_state.split_calculation['split_calculation']
            
            st.markdown("### 📊 **Split Calculation Results**")
            
            # Previous occupier details
            prev_data = split_calc['previous_occupier']
            st.success(f"**Previous Occupier:** {prev_data['days']} days = £{prev_data['amount']:.1f}")
            st.write(f"Period: {prev_data['period']}")
            
            # New occupier details  
            new_data = split_calc['new_occupier']
            st.success(f"**New Occupier:** {new_data['days']} days = £{new_data['amount']:.1f}")
            st.write(f"Period: {new_data['period']}")
            
            # Void period details
            void_data = split_calc['void_period']
            if void_data['days'] > 0:
                st.warning(f"**Void Period:** {void_data['days']} days = £{void_data['amount']:.1f} (written off)")
                st.write(f"Period: {void_data['period']}")
            else:
                st.info("**No void period** (occupiers transitioned on same day)")
            
            # Action buttons
            st.markdown("### 🚀 **Execute Split Actions**")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("📝 Adjust Previous Invoice", type="primary", use_container_width=True):
                    # Execute the split
                    new_contact_id = st.session_state.new_contact.get('ContactID')
                    split_result = execute_split(invoice, new_contact_id, st.session_state.split_calculation)
                    
                    if split_result and split_result.get('success'):
                        st.success("✅ Invoice split executed successfully!")
                        st.write(f"• Adjusted previous invoice to: £{split_result['previous_amount']:.1f}")
                        st.write(f"• Created new invoice for: £{split_result['new_amount']:.1f}")
                        st.session_state.split_executed = True
                        st.rerun()
                    else:
                        error_msg = split_result.get('error', 'Unknown error') if split_result else 'Split execution failed'
                        st.error(f"❌ Split execution failed: {error_msg}")
            
            with col2:
                if st.button("❌ Cancel Split", type="secondary", use_container_width=True):
                    # Cancel and return to previous contact management
                    st.session_state.invoice_splitting_mode = False
                    st.session_state.invoice_to_split = None
                    st.session_state.split_calculation = None
                    st.session_state.split_executed = False
                    st.rerun()
            
            with col3:
                if st.button("🔄 Recalculate", type="secondary", use_container_width=True):
                    # Clear calculation to allow new dates
                    st.session_state.split_calculation = None
                    st.rerun()
        
        # Show completion and return to handle workflow
        if st.session_state.split_executed:
            st.success("🎉 **Invoice splitting completed successfully!**")
            st.info("You can now complete the previous contact workflow.")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button("🔄 Complete Previous Contact Workflow", type="primary", use_container_width=True):
                    # Now execute the handle workflow
                    old_contact_id = st.session_state.existing_contact.get('ContactID')
                    result = handle_previous_contact_workflow(old_contact_id)
                    
                    if result.get('success') or result.get('added_to_previous_group'):
                        st.success("✅ Previous contact workflow completed successfully!")
                        st.session_state.previous_contact_processed = True
                        # Clear splitting state
                        st.session_state.invoice_splitting_mode = False
                        st.session_state.invoice_to_split = None
                        st.session_state.split_calculation = None
                        st.session_state.split_executed = False
                        st.rerun()
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        st.error(f"❌ Workflow reported failure: {error_msg}")
            
            with col2:
                if st.button("🆕 Start New Workflow", type="secondary", use_container_width=True):
                    # Reset everything
                    keys_to_clear = [
                        'existing_contact', 'search_performed', 'new_contact', 'found_invoices', 
                        'selected_invoices', 'found_repeating_templates', 'previous_contact_balance', 
                        'previous_contact_processed', 'contact_validation_result', 'selected_contact_option',
                        'invoice_splitting_mode', 'invoice_to_split', 'split_calculation', 'split_executed',
                        'vacate_date', 'move_in_date'
                    ]
                    for key in keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
    
    # ============================================================================
    # WORKFLOW SUMMARY (Updated to include splitting workflow)
    # ============================================================================
    
    # Show workflow summary when new contact is created (but not when in splitting mode)
    if (st.session_state.new_contact and st.session_state.existing_contact and 
        not st.session_state.invoice_splitting_mode):
        
        # Only show completion message if previous contact was actually processed
        if st.session_state.previous_contact_processed:
            st.markdown("---")
            st.success("🎉 **Workflow Complete!** All steps finished successfully.")
        else:
            # Show what's been completed so far
            st.markdown("---")
            st.info("📋 **Workflow In Progress** - Complete the previous contact step above to finish.")
        
        # Always show comprehensive summary of what's been done
        st.markdown("### 📋 **Workflow Summary**")
        
        # 1. Contact Creation Summary
        if st.session_state.existing_contact and st.session_state.new_contact:
            st.markdown("**1️⃣ Contact Creation:**")
            original_name = st.session_state.existing_contact.get('Name', 'Unknown')
            original_account = st.session_state.existing_contact.get('AccountNumber', 'N/A')
            new_name = st.session_state.new_contact.get('Name', 'Unknown')
            new_account = st.session_state.new_contact.get('AccountNumber', 'N/A')
            
            st.write(f"• ✅ **Found existing contact:** {original_name} ({original_account})")
            st.write(f"• ✅ **Created new contact:** {new_name} ({new_account})")
        
        # 2. Invoice Reassignment Summary
        st.markdown("**2️⃣ Invoice Reassignment:**")
        if st.session_state.found_invoices:
            total_found = len(st.session_state.found_invoices)
            st.write(f"• ✅ **Found {total_found} invoices** for potential reassignment")
            
            # Check if any invoices were actually reassigned
            if len(st.session_state.selected_invoices) == 0:
                # Invoices were likely reassigned (selected_invoices gets cleared after reassignment)
                st.write(f"• ✅ **Successfully reassigned invoices** from old to new contact")
            else:
                st.write(f"• ℹ️ **{len(st.session_state.selected_invoices)} invoices still selected** (not yet reassigned)")
        else:
            st.write("• ℹ️ **No invoices found** for reassignment")
        
        # 3. Template Reassignment Summary
        st.markdown("**3️⃣ Repeating Invoice Template:**")
        if st.session_state.template_search_performed:
            if st.session_state.found_repeating_templates:
                # Check if templates list is empty (would mean it was reassigned and cleared)
                if len(st.session_state.found_repeating_templates) == 0:
                    st.write(f"• ✅ **Template found and reassigned** from old to new contact")
                else:
                    template = st.session_state.found_repeating_templates[0]
                    template_ref = template.get('Reference', 'N/A')
                    st.write(f"• ✅ **Found template:** {template_ref}")
                    st.write(f"• ⚠️ **Template may not have been reassigned yet**")
            else:
                st.write("• ℹ️ **No repeating invoice template** found")
        else:
            st.write("• ⚠️ **Template search not performed**")
        
        # 4. Previous Contact Handling Summary (UPDATED to include splitting)
        st.markdown("**4️⃣ Previous Contact Management:**")
        if st.session_state.previous_contact_balance:
            balance_info = st.session_state.previous_contact_balance
            outstanding = balance_info['outstanding']
            has_balance = balance_info['has_balance']
            old_name = st.session_state.existing_contact.get('Name', 'Unknown')
            
            st.write(f"• ✅ **Checked balance:** ${outstanding:.2f} outstanding")
            
            # Show splitting status if it was used
            if st.session_state.split_executed:
                st.write(f"• ✅ **Invoice splitting completed** - split invoice between occupiers")
            
            if st.session_state.previous_contact_processed:
                if has_balance:
                    st.write(f"• ✅ **Set to ACTIVE + /P code** (has outstanding balance)")
                else:
                    st.write(f"• ✅ **Set to INACTIVE + /P code** (zero balance)")
                    
                st.write(f"• ✅ **Moved to contact group:** '+ Previous accounts still due'")
                st.write(f"• ✅ **Previous contact processed:** {old_name}")
        
        # 5. Final Status
        if st.session_state.previous_contact_processed:
            st.markdown("**✅ All modules completed successfully!**")
        else:
            st.markdown("**⚠️ Previous contact step still pending** - Complete Section 5 above to finish")
        
        # Add restart option
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            button_text = "🆕 Start New Workflow" if st.session_state.previous_contact_processed else "🔄 Reset Current Workflow"
            if st.button(button_text, type="primary", use_container_width=True):
                keys_to_clear = [
                    'existing_contact', 'search_performed', 'new_contact', 'found_invoices', 
                    'selected_invoices', 'found_repeating_templates', 'previous_contact_balance', 
                    'previous_contact_processed', 'contact_validation_result', 'selected_contact_option',
                    'invoice_splitting_mode', 'invoice_to_split', 'split_calculation', 'split_executed',
                    'vacate_date', 'move_in_date'
                ]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

if __name__ == "__main__":
    if check_password():
        main()
