"""
Xero Contact Manager - GUI Interface
===================================

This module provides a graphical user interface for creating new property contacts
in Xero by duplicating existing contacts with modifications.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from typing import Optional, Dict, Any

# Import our modules
from contact_manager import XeroContactManager, create_new_property_contact
from constants import CONTACT_CODES, validate_account_number, parse_account_number


class XeroContactGUI:
    """Main GUI application for Xero Contact Management."""
    
    def __init__(self, root):
        """Initialize the GUI application."""
        self.root = root
        self.root.title("Xero Contact Manager - Property Contact Creator")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Initialize variables
        self.existing_contact = None
        self.contact_manager = None
        
        # Set up the GUI
        self.setup_styles()
        self.create_widgets()
        self.setup_layout()
        
    def setup_styles(self):
        """Configure the visual styles for the application."""
        style = ttk.Style()
        style.theme_use('clam')  # Use a modern theme
        
        # Configure custom styles
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Heading.TLabel', font=('Arial', 10, 'bold'))
        style.configure('Success.TLabel', foreground='green', font=('Arial', 10, 'bold'))
        style.configure('Error.TLabel', foreground='red', font=('Arial', 10, 'bold'))
        
    def create_widgets(self):
        """Create all GUI widgets."""
        # Main title
        self.title_label = ttk.Label(
            self.root, 
            text="Xero Property Contact Creator", 
            style='Title.TLabel'
        )
        
        # ============================================================================
        # SECTION 1: Search Existing Contact
        # ============================================================================
        self.search_frame = ttk.LabelFrame(self.root, text="1. Find Existing Contact", padding="10")
        
        ttk.Label(self.search_frame, text="Account Number:", style='Heading.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 5))
        
        self.account_entry = ttk.Entry(self.search_frame, width=30, font=('Arial', 11))
        self.account_entry.grid(row=1, column=0, sticky='ew', padx=(0, 10))
        
        self.search_button = ttk.Button(
            self.search_frame, 
            text="Search Contact", 
            command=self.search_contact_thread
        )
        self.search_button.grid(row=1, column=1, sticky='w')
        
        # Search results display
        self.search_result_label = ttk.Label(self.search_frame, text="")
        self.search_result_label.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        
        # Contact details display
        self.contact_details_text = scrolledtext.ScrolledText(
            self.search_frame, 
            height=6, 
            width=70, 
            state='disabled',
            font=('Courier', 9)
        )
        self.contact_details_text.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        
        self.search_frame.columnconfigure(0, weight=1)
        
        # ============================================================================
        # SECTION 2: New Contact Details
        # ============================================================================
        self.details_frame = ttk.LabelFrame(self.root, text="2. New Contact Details", padding="10")
        self.details_frame.columnconfigure(1, weight=1)
        
        # Contact Code selection
        ttk.Label(self.details_frame, text="Contact Code:*", style='Heading.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 5))
        
        self.contact_code_var = tk.StringVar()
        self.contact_code_combo = ttk.Combobox(
            self.details_frame, 
            textvariable=self.contact_code_var,
            state="readonly",
            width=15
        )
        
        # Populate contact codes
        contact_codes = list(CONTACT_CODES.keys())
        contact_codes.sort()
        self.contact_code_combo['values'] = contact_codes
        self.contact_code_combo.grid(row=0, column=1, sticky='w', pady=(0, 5))
        
        # Contact code description
        self.code_description_label = ttk.Label(self.details_frame, text="", foreground='blue')
        self.code_description_label.grid(row=0, column=2, sticky='w', padx=(10, 0), pady=(0, 5))
        
        # Bind event to show description
        self.contact_code_combo.bind('<<ComboboxSelected>>', self.on_contact_code_change)
        
       # First Name (required)
        ttk.Label(self.details_frame, text="First Name:*", style='Heading.TLabel').grid(row=1, column=0, sticky='w', pady=(10, 5))
        self.first_name_entry = ttk.Entry(self.details_frame, width=30)
        self.first_name_entry.insert(0, "Occupier")  # Pre-fill with default value
        self.first_name_entry.grid(row=1, column=1, sticky='ew', pady=(10, 5))
        
        # Last Name (optional)
        ttk.Label(self.details_frame, text="Last Name:", style='Heading.TLabel').grid(row=2, column=0, sticky='w', pady=(5, 5))
        self.last_name_entry = ttk.Entry(self.details_frame, width=30)
        self.last_name_entry.grid(row=2, column=1, sticky='ew', pady=(5, 5))
        
        # Email (optional)
        ttk.Label(self.details_frame, text="Email Address:", style='Heading.TLabel').grid(row=3, column=0, sticky='w', pady=(5, 5))
        self.email_entry = ttk.Entry(self.details_frame, width=30)
        self.email_entry.grid(row=3, column=1, sticky='ew', pady=(5, 5))
        
        # Required fields note
        ttk.Label(
            self.details_frame, 
            text="* Required fields", 
            font=('Arial', 8), 
            foreground='gray'
        ).grid(row=4, column=0, columnspan=3, sticky='w', pady=(10, 0))
        
        # ============================================================================
        # SECTION 3: Create Contact
        # ============================================================================
        self.create_frame = ttk.LabelFrame(self.root, text="3. Create New Contact", padding="10")
        
        self.create_button = ttk.Button(
            self.create_frame, 
            text="Create New Contact", 
            command=self.create_contact_thread,
            state='disabled'  # Initially disabled
        )
        self.create_button.pack(pady=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.create_frame, 
            mode='indeterminate', 
            length=400
        )
        self.progress.pack(pady=(0, 10))
        
        # Status/Result display
        self.result_label = ttk.Label(self.create_frame, text="")
        self.result_label.pack(pady=(0, 10))
        
        # Result details
        self.result_text = scrolledtext.ScrolledText(
            self.create_frame, 
            height=8, 
            width=70, 
            state='disabled',
            font=('Courier', 9)
        )
        self.result_text.pack()
        
        # ============================================================================
        # Bottom buttons
        # ============================================================================
        self.button_frame = ttk.Frame(self.root)
        
        self.clear_button = ttk.Button(
            self.button_frame, 
            text="Clear All", 
            command=self.clear_all
        )
        self.clear_button.pack(side='left', padx=(0, 10))
        
        self.exit_button = ttk.Button(
            self.button_frame, 
            text="Exit", 
            command=self.root.quit
        )
        self.exit_button.pack(side='right')
        
    def setup_layout(self):
        """Arrange all widgets in the main window."""
        padding = 10
        
        self.title_label.pack(pady=(padding, padding*2))
        
        self.search_frame.pack(fill='x', padx=padding, pady=(0, padding))
        
        self.details_frame.pack(fill='x', padx=padding, pady=(0, padding))
        
        self.create_frame.pack(fill='both', expand=True, padx=padding, pady=(0, padding))
        
        self.button_frame.pack(fill='x', padx=padding, pady=(0, padding))
    
    def on_contact_code_change(self, event):
        """Update the contact code description when selection changes."""
        selected_code = self.contact_code_var.get()
        if selected_code in CONTACT_CODES:
            description = CONTACT_CODES[selected_code]
            self.code_description_label.config(text=description)
        else:
            self.code_description_label.config(text="")
    
    def search_contact_thread(self):
        """Search for contact in a separate thread to prevent GUI freezing."""
        threading.Thread(target=self.search_contact, daemon=True).start()
    
    def search_contact(self):
        """Search for the existing contact in Xero."""
        account_number = self.account_entry.get().strip()
        
        if not account_number:
            self.update_search_result("Please enter an account number", "error")
            return
        
        if len(account_number) != 8 and not validate_account_number(account_number):
            self.update_search_result("Invalid account number format", "error")
            return
        
        # Update GUI to show searching
        self.root.after(0, lambda: self.search_button.config(state='disabled', text='Searching...'))
        self.update_search_result("Searching for contact...", "info")
        
        try:
            # Initialize contact manager if not already done
            if not self.contact_manager:
                self.contact_manager = XeroContactManager()
                
                # Authenticate
                self.update_search_result("Authenticating with Xero...", "info")
                if not self.contact_manager.authenticate():
                    self.update_search_result("Failed to authenticate with Xero", "error")
                    return
            
            # Search for contact
            self.existing_contact = self.contact_manager.search_contact_by_account_number(account_number)
            
            if self.existing_contact:
                self.update_search_result("Contact found successfully!", "success")
                self.display_contact_details(self.existing_contact)
                
                # Enable the create button
                self.root.after(0, lambda: self.create_button.config(state='normal'))
            else:
                self.update_search_result("No contact found with that account number", "error")
                self.existing_contact = None
                
        except Exception as e:
            self.update_search_result(f"Error searching for contact: {str(e)}", "error")
            self.existing_contact = None
        
        finally:
            # Re-enable search button
            self.root.after(0, lambda: self.search_button.config(state='normal', text='Search Contact'))
    
    def update_search_result(self, message: str, message_type: str = "info"):
        """Update the search result label."""
        def update():
            if message_type == "success":
                self.search_result_label.config(text=message, style='Success.TLabel')
            elif message_type == "error":
                self.search_result_label.config(text=message, style='Error.TLabel')
            else:
                self.search_result_label.config(text=message, style='TLabel')
        
        self.root.after(0, update)
    
    def display_contact_details(self, contact: Dict[str, Any]):
        """Display the found contact details."""
        def update():
            self.contact_details_text.config(state='normal')
            self.contact_details_text.delete(1.0, tk.END)
            
            # Format contact details
            details = f"Contact Name: {contact.get('Name', 'N/A')}\n"
            details += f"Account Number: {contact.get('AccountNumber', 'N/A')}\n"
            details += f"Status: {contact.get('ContactStatus', 'N/A')}\n"
            
            # Add addresses if available
            if contact.get('Addresses'):
                for i, addr in enumerate(contact['Addresses']):
                    details += f"\nAddress {i+1} ({addr.get('AddressType', 'Unknown')}):\n"
                    if addr.get('AddressLine1'):
                        details += f"  {addr['AddressLine1']}\n"
                    if addr.get('AddressLine2'):
                        details += f"  {addr['AddressLine2']}\n"
                    if addr.get('City'):
                        details += f"  {addr['City']}"
                    if addr.get('PostalCode'):
                        details += f" {addr['PostalCode']}"
                    if addr.get('Country'):
                        details += f", {addr['Country']}"
                    details += "\n"
            
            # Add phones if available
            if contact.get('Phones'):
                details += "\nPhone Numbers:\n"
                for phone in contact['Phones']:
                    phone_type = phone.get('PhoneType', 'Unknown')
                    phone_number = phone.get('PhoneNumber', 'N/A')
                    details += f"  {phone_type}: {phone_number}\n"
            
            self.contact_details_text.insert(1.0, details)
            self.contact_details_text.config(state='disabled')
        
        self.root.after(0, update)
    
    def create_contact_thread(self):
        """Create the new contact in a separate thread."""
        threading.Thread(target=self.create_contact, daemon=True).start()
    
    def create_contact(self):
        """Create the new contact with the provided details."""
        # Validate inputs
        contact_code = self.contact_code_var.get()
        first_name = self.first_name_entry.get().strip()
        last_name = self.last_name_entry.get().strip()
        email = self.email_entry.get().strip()
        
        if not contact_code:
            self.update_result("Please select a contact code", "error")
            return
        
        if not first_name:
            self.update_result("Please enter a first name", "error")
            return
        
        if not self.existing_contact:
            self.update_result("Please search for an existing contact first", "error")
            return
        
        # Update GUI to show progress
        self.root.after(0, lambda: self.create_button.config(state='disabled'))
        self.root.after(0, lambda: self.progress.start())
        self.update_result("Creating new contact...", "info")
        
        try:
            original_account = self.existing_contact.get('AccountNumber', '')
            
            # Use the contact manager to create new contact
            new_contact_data = {
                'contact_code': contact_code,
                'first_name': first_name,
                'last_name': last_name,
                'email': email
            }
            
            new_contact = self.contact_manager.create_new_contact(self.existing_contact, new_contact_data)
            
            if new_contact:
                self.update_result("✅ Contact created successfully!", "success")
                self.display_new_contact_details(new_contact, original_account)
            else:
                self.update_result("❌ Failed to create contact", "error")
                
        except Exception as e:
            self.update_result(f"Error creating contact: {str(e)}", "error")
        
        finally:
            # Stop progress bar and re-enable button
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.create_button.config(state='normal'))
    
    def update_result(self, message: str, message_type: str = "info"):
        """Update the result label."""
        def update():
            if message_type == "success":
                self.result_label.config(text=message, style='Success.TLabel')
            elif message_type == "error":
                self.result_label.config(text=message, style='Error.TLabel')
            else:
                self.result_label.config(text=message, style='TLabel')
        
        self.root.after(0, update)
    
    def display_new_contact_details(self, new_contact: Dict[str, Any], original_account: str):
        """Display the created contact details."""
        def update():
            self.result_text.config(state='normal')
            self.result_text.delete(1.0, tk.END)
            
            result = "NEW CONTACT CREATED SUCCESSFULLY\n"
            result += "=" * 50 + "\n\n"
            
            result += f"Original Account: {original_account}\n"
            result += f"New Contact Name: {new_contact.get('Name', 'N/A')}\n"
            result += f"New Account Number: {new_contact.get('AccountNumber', 'N/A')}\n"
            result += f"Contact ID: {new_contact.get('ContactID', 'N/A')}\n"
            result += f"Status: {new_contact.get('ContactStatus', 'N/A')}\n"
            
            # Add group assignment status
            if new_contact.get('group_assignment'):
                result += f"Group Assignment: {new_contact.get('group_assignment')}\n"
            
            # Add contact person details
            if new_contact.get('ContactPersons'):
                result += "\nContact Person:\n"
                person = new_contact['ContactPersons'][0]
                result += f"  Name: {person.get('FirstName', '')} {person.get('LastName', '')}\n"
                if person.get('EmailAddress'):
                    result += f"  Email: {person.get('EmailAddress')}\n"
            
            result += f"\nCreated at: {new_contact.get('UpdatedDateUTC', 'N/A')}\n"
            
            self.result_text.insert(1.0, result)
            self.result_text.config(state='disabled')
        
        self.root.after(0, update)
    
    def clear_all(self):
        """Clear all form fields and results."""
        # Clear entry fields
        self.account_entry.delete(0, tk.END)
        self.contact_code_var.set("")
        self.first_name_entry.delete(0, tk.END)
        self.first_name_entry.insert(0, "Occupier")  # Restore default value
        self.last_name_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        
        # Clear displays
        self.search_result_label.config(text="")
        self.code_description_label.config(text="")
        self.result_label.config(text="")
        
        # Clear text areas
        self.contact_details_text.config(state='normal')
        self.contact_details_text.delete(1.0, tk.END)
        self.contact_details_text.config(state='disabled')
        
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        self.result_text.config(state='disabled')
        
        # Reset variables
        self.existing_contact = None
        
        # Disable create button
        self.create_button.config(state='disabled')


def main():
    """Main function to run the GUI application."""
    root = tk.Tk()
    app = XeroContactGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred:\n{str(e)}")


if __name__ == "__main__":
    main()