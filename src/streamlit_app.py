"""
Xero Contact Manager - Streamlit Interface
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
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔒 Xero Property Manager")
        st.subheader("Please enter password to continue")
        
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if password == st.secrets["APP_PASSWORD"]:
                st.session_state.authenticated = True
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
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if 'contact_manager' not in st.session_state:
    st.session_state.contact_manager = None
if 'existing_contact' not in st.session_state:
    st.session_state.existing_contact = None
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
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
    """Display contact details in a formatted way."""
    st.subheader(title)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Basic Information:**")
        st.write(f"• **Name:** {contact.get('Name', 'N/A')}")
        st.write(f"• **Account Number:** {contact.get('AccountNumber', 'N/A')}")
        st.write(f"• **Status:** {contact.get('ContactStatus', 'N/A')}")
        if contact.get('ContactID'):
            st.write(f"• **Contact ID:** {contact.get('ContactID')}")
    
    with col2:
        # Display addresses
        if contact.get('Addresses'):
            st.write("**Addresses:**")
            for i, addr in enumerate(contact['Addresses']):
                st.write(f"**{addr.get('AddressType', 'Unknown')} Address:**")
                address_lines = []
                if addr.get('AddressLine1'):
                    address_lines.append(addr['AddressLine1'])
                if addr.get('AddressLine2'):
                    address_lines.append(addr['AddressLine2'])
                if addr.get('City'):
                    city_line = addr['City']
                    if addr.get('PostalCode'):
                        city_line += f" {addr['PostalCode']}"
                    if addr.get('Country'):
                        city_line += f", {addr['Country']}"
                    address_lines.append(city_line)
                
                for line in address_lines:
                    st.write(f"  {line}")
        
        # Display phones
        if contact.get('Phones'):
            st.write("**Phone Numbers:**")
            for phone in contact['Phones']:
                phone_type = phone.get('PhoneType', 'Unknown')
                phone_number = phone.get('PhoneNumber', 'N/A')
                st.write(f"• {phone_type}: {phone_number}")

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
    st.title("🏢 Xero Property Contact Creator")
    st.markdown("---")
    
    # Sidebar for navigation and info
    with st.sidebar:
        st.header("Multi-Module System")
        
        st.markdown("### Module 1: Contact Creation")
        st.info("Create new tenant/owner contacts by duplicating existing property contacts with modifications.")
        
        st.markdown("### Module 2: Invoice Reassignment")
        st.info("Reassign invoices from old contacts to new contacts based on move-in date.")
        
        st.markdown("### Module 3: Previous Contact Management")
        st.info("Handle previous contact status based on outstanding balance.")
        
        if st.button("Clear All Data", type="secondary"):
            # Reset all session state
            keys_to_clear = [
                'existing_contact', 'search_performed', 'contact_manager', 
                'authenticated', 'new_contact', 'found_invoices', 
                'selected_invoices', 'invoice_search_performed',
                'found_repeating_templates', 'template_search_performed',
                'previous_contact_balance', 'previous_contact_processed'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        # Display connection status
        st.markdown("### Connection Status")
        if st.session_state.authenticated:
            st.success("🟢 Connected to Xero")
        else:
            st.warning("🟡 Not connected")
        
        # Show progress through modules
        st.markdown("### Workflow Progress")
        if st.session_state.existing_contact:
            st.success("✅ Found existing contact")
        else:
            st.info("1️⃣ Search for existing contact")
            
        if st.session_state.new_contact:
            st.success("✅ Created new contact")
        else:
            st.info("2️⃣ Create new contact")
            
        if st.session_state.new_contact:
            st.info("3️⃣ Ready for invoice reassignment")
        
        if st.session_state.previous_contact_processed:
            st.success("✅ Previous contact handled")
        elif st.session_state.new_contact:
            st.info("4️⃣ Ready for previous contact handling")
        
        # Add debug section
        st.markdown("---")
        st.markdown("### 🐛 Debug Mode")
        debug_mode = st.checkbox("Enable Invoice Search Testing", help="Test invoice search without creating contacts")
        
        if debug_mode:
            st.markdown("**Quick Invoice Search Test:**")
            
            # Option 1: Use Contact ID directly
            with st.expander("Option 1: Direct Contact ID Search", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    test_contact_id = st.text_input(
                        "Contact ID (UUID format)", 
                        placeholder="e.g., 025867f1-d741-4d6b-b1af-9ac774b59ba7",
                        help="Get this from an existing contact in Xero",
                        key="direct_contact_id"
                    )
                
                with col2:
                    test_date = st.date_input(
                        "Move-in Date", 
                        value=date.today(),
                        help="Search for invoices after this date",
                        key="direct_test_date"
                    )
                
                if st.button("🔍 Test Invoice Search", type="secondary", key="direct_test"):
                    if test_contact_id:
                        # Authenticate if needed
                        if not st.session_state.authenticated:
                            authenticate_xero()
                        
                        if st.session_state.authenticated:
                            invoices = search_invoices_for_old_contact(test_contact_id, test_date)
                            if invoices:
                                st.success(f"✅ Found {len(invoices)} invoices!")
                                # Show basic invoice info
                                for inv in invoices:
                                    st.write(f"• {inv.get('InvoiceNumber', 'N/A')} - {inv.get('Status', 'N/A')} - ${inv.get('Total', 0)}")
                            else:
                                st.warning("No invoices found - check terminal for debug output")
                    else:
                        st.error("Please enter a Contact ID")
            
            # Option 2: Search by Account Number first to get Contact ID
            with st.expander("Option 2: Find Contact ID from Account Number", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    account_search = st.text_input(
                        "Account Number", 
                        placeholder="e.g., ANP001011 or ANP001011/3B",
                        help="Enter account number to find Contact ID",
                        key="account_search"
                    )
                
                with col2:
                    test_date2 = st.date_input(
                        "Move-in Date", 
                        value=date.today(),
                        help="Search for invoices after this date",
                        key="account_test_date"
                    )
                
                if st.button("1. Find Contact ID", type="secondary", key="find_contact"):
                    if account_search:
                        # Authenticate if needed
                        if not st.session_state.authenticated:
                            authenticate_xero()
                        
                        if st.session_state.authenticated:
                            contact = search_contact(account_search.strip().upper())
                            if contact:
                                contact_id = contact.get('ContactID')
                                contact_name = contact.get('Name', 'Unknown')
                                
                                st.success(f"✅ Found Contact!")
                                st.info(f"**Name:** {contact_name}\n\n**Contact ID:** `{contact_id}`")
                                
                                # Auto-populate for next step
                                st.session_state.debug_found_contact_id = contact_id
                                st.session_state.debug_contact_name = contact_name
                            else:
                                st.error("❌ Contact not found")
                    else:
                        st.error("Please enter an Account Number")
                
                # Step 2: Search invoices if we have a contact
                if hasattr(st.session_state, 'debug_found_contact_id'):
                    st.markdown(f"**Found Contact:** {st.session_state.debug_contact_name}")
                    st.code(f"Contact ID: {st.session_state.debug_found_contact_id}")
                    
                    if st.button("2. 🔍 Search Invoices for This Contact", type="primary", key="search_with_found"):
                        invoices = search_invoices_for_old_contact(st.session_state.debug_found_contact_id, test_date2)
                        if invoices:
                            st.success(f"✅ Found {len(invoices)} invoices!")
                            # Show basic invoice info
                            for inv in invoices:
                                st.write(f"• {inv.get('InvoiceNumber', 'N/A')} - {inv.get('Status', 'N/A')} - ${inv.get('Total', 0)}")
                        else:
                            st.warning("No invoices found - check terminal for debug output")
    
    # Main content area
    
    # ============================================================================
    # SECTION 1: Search Existing Contact
    # ============================================================================
    
    with st.expander("1️⃣ Find Existing Contact", expanded=True):
        st.markdown("Enter an account number to search for an existing contact:")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            account_number = st.text_input(
                "Account Number",
                placeholder="e.g., ANP001042 or ANP001042/3B",
                help="Enter full account number or first 8 characters for property search"
            )
        
        with col2:
            search_clicked = st.button("🔍 Search Contact", type="primary")
        
        # Handle search
        if search_clicked and account_number:
            # Validate input
            account_number = account_number.strip().upper()
            
            if len(account_number) != 8 and not validate_account_number(account_number):
                st.error("❌ Invalid account number format")
            else:
                contact = search_contact(account_number)
                
                if contact:
                    st.success("✅ Contact found successfully!")
                    display_contact_details(contact, "Found Contact Details")
                else:
                    st.error("❌ No contact found with that account number")
        
        elif search_clicked and not account_number:
            st.error("❌ Please enter an account number")
    
    # ============================================================================
    # SECTION 2: New Contact Details (only show if contact found)
    # ============================================================================
    
    if st.session_state.existing_contact:
        with st.expander("2️⃣ New Contact Details", expanded=True):
            st.markdown("Enter details for the new contact:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Contact Code selection
                st.markdown("**Contact Code:** *")
                contact_codes = list(CONTACT_CODES.keys())
                contact_codes.sort()
                
                selected_code = st.selectbox(
                    "Select contact code",
                    options=contact_codes,
                    index=None,
                    placeholder="Choose a contact code..."
                )
                
                if selected_code:
                    st.info(f"📋 {CONTACT_CODES[selected_code]}")
                
                # First Name (required)
                st.markdown("**First Name:** *")
                first_name = st.text_input(
                    "First Name",
                    value="Occupier",
                    placeholder="Enter first name"
                )
            
            with col2:
                # Last Name (optional)
                st.markdown("**Last Name:**")
                last_name = st.text_input(
                    "Last Name",
                    placeholder="Enter last name (optional)"
                )
                
                # Email (optional)
                st.markdown("**Email Address:**")
                email = st.text_input(
                    "Email Address",
                    placeholder="Enter email address (optional)"
                )
            
            st.caption("* Required fields")
            
            # ============================================================================
            # SECTION 3: Create Contact
            # ============================================================================
            
            st.markdown("---")
            st.markdown("### 3️⃣ Create New Contact")
            
            # Validation
            can_create = bool(selected_code and first_name.strip())
            
            if not can_create:
                missing = []
                if not selected_code:
                    missing.append("Contact Code")
                if not first_name.strip():
                    missing.append("First Name")
                st.warning(f"⚠️ Please provide: {', '.join(missing)}")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                create_clicked = st.button(
                    "🆕 Create New Contact",
                    type="primary",
                    disabled=not can_create,
                    use_container_width=True
                )
            
            # Handle contact creation
            if create_clicked and can_create:
                new_contact_data = {
                    'contact_code': selected_code,
                    'first_name': first_name.strip(),
                    'last_name': last_name.strip(),
                    'email': email.strip()
                }
                
                new_contact = create_new_contact(new_contact_data)
                
                if new_contact:
                    st.success("🎉 Contact created successfully!")
                    
                    # Display results
                    st.markdown("---")
                    display_contact_details(new_contact, "✅ New Contact Created")
                    
                    # Show additional info
                    if new_contact.get('group_assignment'):
                        st.info(f"👥 Group Assignment: {new_contact.get('group_assignment')}")
                    
                    # Show summary
                    original_account = st.session_state.existing_contact.get('AccountNumber', 'N/A')
                    new_account = new_contact.get('AccountNumber', 'N/A')
                    
                    st.success(f"✅ **Summary:**\n"
                             f"• Original Account: `{original_account}`\n"
                             f"• New Account: `{new_account}`\n"
                             f"• Contact ID: `{new_contact.get('ContactID', 'N/A')}`")
                else:
                    st.error("❌ Failed to create contact. Please check the logs and try again.")
    
    # ============================================================================
    # MODULE 2: Invoice Reassignment (only show if new contact created)
    # ============================================================================
    
    if st.session_state.new_contact and st.session_state.existing_contact:
        st.markdown("---")
        st.markdown("## 🧾 Module 2: Invoice Reassignment")
        
        with st.expander("4️⃣ Reassign Invoices to New Contact", expanded=True):
            st.markdown("Search for invoices assigned to the old contact that need to be reassigned:")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**Move-in Date:** *")
                move_in_date = st.date_input(
                    "Select the date when the new occupier moved in",
                    value=date.today(),
                    help="Invoices issued after this date will be found for reassignment"
                )
            
            with col2:
                st.markdown("**Search Invoices:**")
                search_invoices_clicked = st.button(
                    "🔍 Find Invoices", 
                    type="primary",
                    help="Search for invoices to reassign"
                )
            
            # Handle invoice search
            if search_invoices_clicked and move_in_date:
                old_contact_id = st.session_state.existing_contact.get('ContactID')
                if old_contact_id:
                    invoices = search_invoices_for_old_contact(old_contact_id, move_in_date)
                    
                    if invoices:
                        st.success(f"✅ Found {len(invoices)} invoices for potential reassignment")
                    else:
                        st.info("ℹ️ No invoices found after the move-in date")
                else:
                    st.error("❌ No contact ID found for old contact")
            
            # Display found invoices
            if st.session_state.found_invoices:
                st.markdown("---")
                st.markdown("### 📋 Invoices Available for Reassignment")
                
                # Create invoice selection interface
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown("**Select invoices to reassign:**")
                
                with col2:
                    if st.button("Select All", type="secondary"):
                        st.session_state.selected_invoices = [
                            inv.get('InvoiceID') for inv in st.session_state.found_invoices
                        ]
                        st.rerun()
                
                # Display invoices with checkboxes
                selected_for_reassignment = []
                
                for i, invoice in enumerate(st.session_state.found_invoices):
                    invoice_id = invoice.get('InvoiceID', '')
                    invoice_number = invoice.get('InvoiceNumber', 'N/A')
                    invoice_date = invoice.get('DateString', 'N/A')
                    status = invoice.get('Status', 'N/A')
                    total = invoice.get('Total', 0)
                    amount_due = invoice.get('AmountDue', 0)
                    
                    # Format date
                    try:
                        if invoice_date != 'N/A':
                            date_obj = datetime.fromisoformat(invoice_date.replace('T00:00:00', ''))
                            formatted_date = date_obj.strftime('%d %b %Y')
                        else:
                            formatted_date = 'N/A'
                    except:
                        formatted_date = invoice_date
                    
                    # Create checkbox for each invoice
                    col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 2])
                    
                    with col1:
                        is_selected = st.checkbox(
                            f"Select",
                            key=f"invoice_select_{i}",
                            value=invoice_id in st.session_state.selected_invoices
                        )
                        
                        if is_selected and invoice_id not in selected_for_reassignment:
                            selected_for_reassignment.append(invoice_id)
                    
                    with col2:
                        st.write(f"**{invoice_number}**")
                    
                    with col3:
                        st.write(f"📅 {formatted_date}")
                    
                    with col4:
                        st.write(f"💰 ${float(total):.2f}")
                    
                    with col5:
                        status_color = {
                            'DRAFT': '🟡',
                            'SUBMITTED': '🟠', 
                            'AUTHORISED': '🟢'
                        }.get(status, '⚪')
                        st.write(f"{status_color} {status}")
                
                # Update selected invoices in session state
                st.session_state.selected_invoices = selected_for_reassignment
                
                # Show reassignment section
                if selected_for_reassignment:
                    st.markdown("---")
                    st.markdown("### 🔄 Confirm Reassignment")
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col2:
                        st.info(f"📊 **Ready to reassign {len(selected_for_reassignment)} invoices**\n\n"
                               f"**From:** {st.session_state.existing_contact.get('Name', 'Unknown')}\n"
                               f"**To:** {st.session_state.new_contact.get('Name', 'Unknown')}")
                        
                        reassign_clicked = st.button(
                            f"🔄 Reassign {len(selected_for_reassignment)} Invoices",
                            type="primary",
                            use_container_width=True
                        )
                    
                    # Handle reassignment
                    if reassign_clicked:
                        new_contact_id = st.session_state.new_contact.get('ContactID')
                        if new_contact_id:
                            successful, failed = reassign_invoices(selected_for_reassignment, new_contact_id)
                            
                            if successful:
                                st.success(f"🎉 Successfully reassigned {len(successful)} invoices!")
                                
                                # Show summary
                                st.markdown("### ✅ Reassignment Summary")
                                if successful:
                                    st.success(f"**✅ Successful ({len(successful)}):**")
                                    for invoice_id in successful:
                                        # Find invoice details
                                        invoice = next((inv for inv in st.session_state.found_invoices 
                                                      if inv.get('InvoiceID') == invoice_id), None)
                                        if invoice:
                                            st.write(f"• {invoice.get('InvoiceNumber', 'N/A')} - ${float(invoice.get('Total', 0)):.2f}")
                                
                                if failed:
                                    st.error(f"**❌ Failed ({len(failed)}):**")
                                    for invoice_id in failed:
                                        invoice = next((inv for inv in st.session_state.found_invoices 
                                                      if inv.get('InvoiceID') == invoice_id), None)
                                        if invoice:
                                            st.write(f"• {invoice.get('InvoiceNumber', 'N/A')}")
                                
                                # Clear selections after successful reassignment
                                st.session_state.selected_invoices = []
                                
                            else:
                                st.error("❌ No invoices were successfully reassigned")
                        else:
                            st.error("❌ No contact ID found for new contact")
        
        # ============================================================================
        # SECTION 5: Repeating Invoice Template Reassignment
        # ============================================================================
        
        st.markdown("---")
        
        with st.expander("5️⃣ Reassign Repeating Invoice Template", expanded=True):
            st.markdown("Transfer recurring invoice template from old contact to new contact:")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.info("ℹ️ **How this works:**\n"
                       "• Searches for repeating invoice template assigned to old contact\n"
                       "• Copies all details (schedule, line items, amounts)\n"
                       "• Creates new template for new contact\n"
                       "• Deletes old template")
            
            with col2:
                search_templates_clicked = st.button(
                    "🔍 Find Repeating Template", 
                    type="primary",
                    help="Search for repeating invoice template"
                )
            
            # Handle template search
            if search_templates_clicked:
                old_contact_id = st.session_state.existing_contact.get('ContactID')
                if old_contact_id:
                    templates = search_repeating_invoices_for_old_contact(old_contact_id)
                    
                    if templates:
                        st.success(f"✅ Found {len(templates)} repeating invoice template(s)")
                    else:
                        st.info("ℹ️ No repeating invoice templates found for old contact")
                else:
                    st.error("❌ No contact ID found for old contact")
            
            # Display found templates
            if st.session_state.found_repeating_templates:
                st.markdown("### 📋 Found Repeating Invoice Template")
                
                template = st.session_state.found_repeating_templates[0]  # Only one expected
                
                # Format template details for display
                schedule = template.get('Schedule', {})
                period = schedule.get('Period', 1)
                unit = schedule.get('Unit', 'MONTHLY').lower()
                frequency = f"Every {period} {unit}" if period > 1 else f"{unit.capitalize()}"
                
                # Display template details
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**Template Details:**")
                    st.write(f"• **Reference:** {template.get('Reference', 'N/A')}")
                    st.write(f"• **Type:** {template.get('Type', 'N/A')}")
                    st.write(f"• **Status:** {template.get('Status', 'N/A')}")
                
                with col2:
                    st.write("**Schedule:**")
                    st.write(f"• **Frequency:** {frequency}")
                    st.write(f"• **Due Date:** {schedule.get('DueDate', 'N/A')} {schedule.get('DueDateType', '')}")
                
                with col3:
                    st.write("**Financial:**")
                    st.write(f"• **Total:** ${float(template.get('Total', 0)):.2f}")
                    st.write(f"• **Line Items:** {len(template.get('LineItems', []))}")
                
                # Show confirmation and reassign section
                st.markdown("---")
                st.markdown("### 🔄 Confirm Template Reassignment")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col2:
                    st.warning(f"⚠️ **Confirm Reassignment**\n\n"
                             f"This will:\n"
                             f"• **Delete** the current template for: {st.session_state.existing_contact.get('Name', 'Unknown')}\n"
                             f"• **Create** a new identical template for: {st.session_state.new_contact.get('Name', 'Unknown')}\n\n"
                             f"**This action cannot be easily undone.**")
                    
                    reassign_template_clicked = st.button(
                        "🔄 Reassign Repeating Invoice Template",
                        type="primary",
                        use_container_width=True
                    )
                
                # Handle template reassignment
                if reassign_template_clicked:
                    old_contact_id = st.session_state.existing_contact.get('ContactID')
                    new_contact_id = st.session_state.new_contact.get('ContactID')
                    
                    if old_contact_id and new_contact_id:
                        result = reassign_repeating_invoice_template(old_contact_id, new_contact_id)
                        
                        if result.get('success'):
                            st.success("🎉 Successfully reassigned repeating invoice template!")
                            
                            # Show summary
                            st.markdown("### ✅ Reassignment Summary")
                            
                            old_template = result.get('found_template', {})
                            new_template = result.get('created_template', {})
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.success("**✅ Old Template (Deleted):**")
                                st.write(f"• ID: {old_template.get('RepeatingInvoiceID', 'N/A')}")
                                st.write(f"• Reference: {old_template.get('Reference', 'N/A')}")
                            
                            with col2:
                                st.success("**✅ New Template (Created):**")
                                st.write(f"• ID: {new_template.get('RepeatingInvoiceID', 'N/A')}")
                                st.write(f"• Reference: {new_template.get('Reference', 'N/A')}")
                            
                            if not result.get('deleted_successfully'):
                                st.warning("⚠️ **Note:** New template created successfully, but old template deletion may have failed. Please check manually in Xero.")
                            
                            # Clear the found templates since reassignment is complete
                            st.session_state.found_repeating_templates = []
                            
                        else:
                            error_msg = result.get('error', 'Unknown error occurred')
                            st.error(f"❌ Failed to reassign template: {error_msg}")
                    else:
                        st.error("❌ Missing contact IDs for reassignment")
        
        # ============================================================================
        # MODULE 3: Previous Contact Management (only show if new contact created)
        # ============================================================================
        
        if st.session_state.new_contact and st.session_state.existing_contact:
            st.markdown("---")
            st.markdown("## 👤 Module 3: Previous Contact Management")
            
            with st.expander("6️⃣ Handle Previous Contact Status", expanded=True):
                st.markdown("Manage the previous contact after successful reassignment:")
                
                old_contact_id = st.session_state.existing_contact.get('ContactID')
                old_contact_name = st.session_state.existing_contact.get('Name', 'Unknown')
                
                if not st.session_state.previous_contact_processed:
                    # Step 1: Check balance
                    if not st.session_state.previous_contact_balance:
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.info(f"ℹ️ **Previous Contact:** {old_contact_name}\n\n"
                                   "We need to check if this contact has any outstanding balance to determine the next action.")
                        
                        with col2:
                            check_balance_clicked = st.button(
                                "💰 Check Balance", 
                                type="primary",
                                help="Check outstanding balance for previous contact"
                            )
                        
                        # Handle balance check
                        if check_balance_clicked and old_contact_id:
                            balance_info = get_previous_contact_balance_info(old_contact_id)
                            
                            if balance_info:
                                st.session_state.previous_contact_balance = balance_info
                                st.rerun()
                            else:
                                st.error("❌ Failed to get balance information")
                    
                    # Step 2: Show balance and action options
                    if st.session_state.previous_contact_balance:
                        balance_info = st.session_state.previous_contact_balance
                        outstanding = balance_info['outstanding']
                        has_balance = balance_info['has_balance']
                        
                        st.markdown("---")
                        st.markdown("### 💰 Balance Status")
                        
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            if has_balance:
                                st.warning(f"⚠️ **Outstanding Balance: ${outstanding:.2f}**\n\n"
                                         f"The previous contact **{old_contact_name}** still has an outstanding balance.\n\n"
                                         "**Recommended Action:**\n"
                                         "• Change contact code to **/P** (Previous account still owing money)\n"
                                         "• Keep contact **ACTIVE** (they still owe money)\n"
                                         "• Move to **'Previous accounts still due'** contact group")
                            else:
                                st.success(f"✅ **Zero Balance: ${outstanding:.2f}**\n\n"
                                         f"The previous contact **{old_contact_name}** has no outstanding balance.\n\n"
                                         "**Recommended Action:**\n"
                                         "• Change contact code to **/P** (Previous account)\n" 
                                         "• Set contact to **INACTIVE** (no longer active)\n"
                                         "• Move to **'Previous accounts still due'** contact group")
                        
                        with col2:
                            if has_balance:
                                st.metric("Outstanding", f"${outstanding:.2f}", delta=None)
                                st.metric("Status", "ACTIVE", delta="Keep Active")
                            else:
                                st.metric("Outstanding", f"${outstanding:.2f}", delta=None)
                                st.metric("Status", "INACTIVE", delta="Archive")
                        
                        with col3:
                            st.metric("Action", "/P Code", delta="Previous")
                            st.metric("Group", "Previous accounts", delta="Move")
                        
                        # Confirmation section
                        st.markdown("---")
                        st.markdown("### 🔄 Confirm Action")
                        
                        col1, col2, col3 = st.columns([1, 2, 1])
                        
                        with col2:
                            action_description = (
                                "Set to INACTIVE + /P code" if not has_balance 
                                else "Keep ACTIVE + /P code"
                            )
                            
                            st.warning(f"⚠️ **Confirm Previous Contact Handling**\n\n"
                                     f"This will:\n"
                                     f"• **{action_description}**\n"
                                     f"• **Remove** from current contact groups\n"
                                     f"• **Add** to 'Previous accounts still due' group\n\n"
                                     f"**This action modifies the contact in Xero.**")
                            
                            handle_previous_clicked = st.button(
                                f"🔄 Handle Previous Contact",
                                type="primary",
                                use_container_width=True
                            )
                        
                        # Handle the workflow
                        if handle_previous_clicked:
                            result = handle_previous_contact_workflow(old_contact_id)
                            
                            if result.get('success'):
                                st.success("🎉 Successfully handled previous contact!")
                                
                                # Show detailed results
                                st.markdown("### ✅ Previous Contact Summary")
                                
                                balance_info = result.get('balance_info', {})
                                outstanding = balance_info.get('outstanding', 0)
                                groups_removed = result.get('groups_removed', [])
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.success("**✅ Actions Completed:**")
                                    status = "INACTIVE" if outstanding == 0 else "ACTIVE"
                                    st.write(f"• **Status:** Set to {status}")
                                    st.write(f"• **Code:** Changed to /P")
                                    st.write(f"• **Balance:** ${outstanding:.2f}")
                                
                                with col2:
                                    st.success("**✅ Group Changes:**")
                                    if groups_removed:
                                        st.write("**Removed from:**")
                                        for group in groups_removed:
                                            st.write(f"  • {group}")
                                    st.write("**Added to:**")
                                    st.write("  • Previous accounts still due")
                                
                                # Mark as processed
                                st.session_state.previous_contact_processed = True
                                
                            else:
                                error_msg = result.get('error', 'Unknown error occurred')
                                st.error(f"❌ Failed to handle previous contact: {error_msg}")
                                
                                # Show partial results if any
                                if result.get('balance_info'):
                                    st.warning("⚠️ **Partial Results:**")
                                    if result.get('contact_updated'):
                                        st.write("✅ Contact updated to /P")
                                    if result.get('added_to_previous_group'):
                                        st.write("✅ Added to previous accounts group")
                                    if result.get('groups_removed'):
                                        st.write(f"✅ Removed from {len(result['groups_removed'])} groups")
                
                else:
                    # Already processed
                    st.success("✅ **Previous Contact Already Handled**\n\n"
                             "The previous contact has been successfully processed and moved to appropriate status.")
                    
                    if st.button("🔄 Process Another Contact", type="secondary"):
                        # Reset for new workflow
                        keys_to_reset = [
                            'existing_contact', 'new_contact', 'found_invoices', 
                            'selected_invoices', 'found_repeating_templates',
                            'previous_contact_balance', 'previous_contact_processed'
                        ]
                        for key in keys_to_reset:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
    
    else:
        # Show message if no contact searched yet
        if not st.session_state.search_performed:
            st.info("👆 Please search for an existing contact first to continue")
        else:
            st.warning("❌ No contact found. Please search again with a different account number.")
    
    # Show instructions for next steps
    if st.session_state.previous_contact_processed:
        st.markdown("---")
        st.success("🎉 **Complete Workflow Finished!** You have successfully:")
        st.write("• ✅ Created new contact")
        st.write("• ✅ Reassigned invoices (if any)")
        st.write("• ✅ Reassigned repeating invoice templates (if any)")
        st.write("• ✅ Handled previous contact status")
        st.write("• ✅ Updated contact groups appropriately")
        
        if st.button("🆕 Start New Workflow", type="primary"):
            # Reset everything for fresh start
            keys_to_clear = [
                'existing_contact', 'search_performed', 'new_contact', 'found_invoices', 
                'selected_invoices', 'invoice_search_performed', 'found_repeating_templates',
                'template_search_performed', 'previous_contact_balance', 'previous_contact_processed'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
            
    elif st.session_state.new_contact:
        st.markdown("---")
        st.success("🎉 **Workflow In Progress!** You can now:")
        st.write("• ✅ Create another contact (Clear All Data)")
        st.write("• ✅ Reassign invoices using Section 4 above")
        st.write("• ✅ Reassign repeating invoice templates using Section 5 above")
        st.write("• ✅ Handle previous contact using Section 6 above")
        st.write("• ✅ Close the application")

if __name__ == "__main__":
    if check_password():
        main()