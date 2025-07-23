# 🏢 Xero Property Contact Management System

A comprehensive property management workflow system for handling tenant/owner transitions, invoice reassignments, and contact lifecycle management through the Xero API.

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-v1.28+-red.svg)
![Xero API](https://img.shields.io/badge/xero_api-v2.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [File Structure](#file-structure)
- [Business Rules](#business-rules)
- [API Integration](#api-integration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🎯 Overview

This system streamlines the complex process of managing property contacts when tenants/owners change, ensuring seamless transition of billing, invoices, and contact records in Xero. Built specifically for property management companies handling recurring billing for services like stair cleaning.

### Problem Solved
When a new tenant moves into a property, property managers need to:
1. Create a new contact in Xero with correct billing details
2. Reassign outstanding invoices to the new contact
3. Transfer recurring billing templates
4. Handle the previous contact appropriately based on outstanding balances

This system automates the entire workflow through an intuitive web interface.

## ✨ Features

### 🏗️ Module 1: Contact Creation
- **Smart Contact Duplication**: Clone existing property contacts with modifications
- **Flexible Account Search**: Search by full account number or property base (8 characters)
- **Contact Code Management**: 15+ predefined billing codes for different scenarios
- **Automatic Group Assignment**: Auto-assign contacts to appropriate contact groups
- **Address & Details Preservation**: Maintain property addresses while updating personal details

### 🧾 Module 2: Invoice Reassignment
- **Invoice Discovery**: Find invoices assigned to old contacts after move-in date
- **Selective Reassignment**: Choose which invoices to reassign with checkbox interface
- **Repeating Template Transfer**: Copy recurring invoice templates with all settings
- **Schedule Preservation**: Maintain exact billing schedules and frequencies
- **Batch Processing**: Handle multiple invoices simultaneously

### 👤 Module 3: Previous Contact Management
- **Balance Checking**: Automatically check outstanding balances via Xero API
- **Smart Status Management**: 
  - Zero balance → Set INACTIVE + /P code
  - Outstanding balance → Keep ACTIVE + /P code
- **Contact Group Migration**: Remove from current groups, add to "Previous accounts still due"
- **Audit Trail**: Complete logging of all changes made

### 🎨 User Interface
- **Streamlit Web Interface**: Modern, responsive web application
- **Progress Tracking**: Visual workflow progress in sidebar
- **Debug Mode**: Built-in testing tools for troubleshooting
- **Error Handling**: User-friendly error messages with detailed logging
- **Confirmation Dialogs**: Prevent accidental changes with clear confirmation steps

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- Xero Custom Connection App with Client Credentials
- Git (for cloning repository)

### Step 1: Clone Repository
```bash
git clone https://github.com/your-username/xero-contact-manager.git
cd xero-contact-manager
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install streamlit requests python-dotenv
```

### Step 4: Create Environment File
```bash
# Create .env file in project root
touch .env
```

## ⚙️ Configuration

### Xero API Setup

1. **Create Xero Custom Connection**:
   - Go to [Xero Developer Portal](https://developer.xero.com)
   - Create new "Custom Connection" app
   - Note down Client ID and Client Secret

2. **Configure Environment Variables**:
```env
# .env file
XERO_CLIENT_ID=your_client_id_here
XERO_CLIENT_SECRET=your_client_secret_here
```

3. **Set Required Scopes**:
   - `accounting.contacts` - For contact management
   - `accounting.transactions` - For invoice operations

### Contact Group Setup
Ensure your Xero organization has the following contact group:
- **"Previous accounts still due"** - For archived contacts

## 📖 Usage

### Starting the Application
```bash
streamlit run src/streamlit_app.py
```

The application will open in your browser at `http://localhost:8501`

### Complete Workflow Guide

#### Step 1: Find Existing Contact
1. Enter account number (e.g., `ANP001042/3B` or `ANP00104` for property search)
2. Click "🔍 Search Contact"
3. Review found contact details

#### Step 2: Create New Contact
1. Select appropriate contact code from dropdown
2. Enter first name (required) and last name (optional)
3. Add email address if available
4. Click "🆕 Create New Contact"
5. Verify new contact details and group assignment

#### Step 3: Reassign Invoices (Optional)
1. Set move-in date for invoice filtering
2. Click "🔍 Find Invoices"
3. Select invoices to reassign using checkboxes
4. Click "🔄 Reassign X Invoices"
5. Review reassignment results

#### Step 4: Reassign Repeating Templates (Optional)
1. Click "🔍 Find Repeating Template"
2. Review template details (schedule, amounts, line items)
3. Click "🔄 Reassign Repeating Invoice Template"
4. Confirm template transfer completed

#### Step 5: Handle Previous Contact
1. Click "💰 Check Balance" to get outstanding amount
2. Review recommended action based on balance:
   - **Zero Balance**: Set INACTIVE + /P code
   - **Outstanding Balance**: Keep ACTIVE + /P code
3. Click "🔄 Handle Previous Contact"
4. Review completion summary

### Debug Mode
Access debug tools via sidebar:
- Test invoice search with specific contact IDs
- Find contact IDs from account numbers
- Troubleshoot API connectivity

## 📁 File Structure

```
xero-contact-manager/
├── src/
│   ├── streamlit_app.py          # Main Streamlit application
│   ├── contact_manager.py        # Module 1: Contact creation logic
│   ├── invoice_manager.py        # Module 2: Invoice reassignment logic
│   ├── previous_contact_manager.py # Module 3: Previous contact handling
│   ├── constants.py              # Business rules and constants
│   └── __init__.py
├── .env                          # Environment variables (not in repo)
├── .gitignore                    # Git ignore file
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

### Core Modules

- **`streamlit_app.py`**: Main web interface orchestrating the complete workflow
- **`contact_manager.py`**: Handles Xero contact creation, duplication, and group management
- **`invoice_manager.py`**: Manages invoice search, reassignment, and repeating template operations
- **`previous_contact_manager.py`**: Handles balance checking and previous contact lifecycle
- **`constants.py`**: Business rules, contact codes, and utility functions

## 📊 Business Rules

### Account Number Structure
```
Format: ABC001234/XX
├── ABC: 3-letter property code
├── 001234: 6-digit property identifier  
├── 4: Sequential counter (9th character)
└── /XX: Contact code suffix
```

### Contact Codes

#### Quarterly Billing
- `/1A` - Invoiced quarterly on the 1st
- `/2A` - Invoiced quarterly on the 5th
- `/1B` - Invoiced quarterly on the 12th
- `/3A` - Invoiced quarterly on the 14th

#### Monthly Billing  
- `/3B` - Invoiced monthly on the 1st
- `/3C` - Invoiced monthly on the 16th
- `/3D` - Invoiced monthly on the 23rd

#### Payment Types
- `/1C` - One person only pays
- `/A` - Current customer on payment plan
- `/B` - Pays by standing order
- `/D` - Pays by Direct Debit

#### Special Situations
- `/P` - Past account still due (person moved out but still owes)
- `/Q` - One off job only
- `/R` - Refuses to pay. Not billed
- `/S` - Stopped cleaning. Not billed anymore

#### Third Party Payers
- `/CR` - Accounts paid by Castlerock/Edinvar/Places for People
- `/LH` - Accounts paid by Link Housing/Curb

### Previous Contact Handling Logic

| Balance Status | Contact Status | Contact Code | Contact Group |
|---------------|----------------|--------------|---------------|
| $0.00 | INACTIVE | /P | Previous accounts still due |
| > $0.00 | ACTIVE | /P | Previous accounts still due |

## 🔗 API Integration

### Authentication
- **Method**: OAuth 2.0 Client Credentials
- **Scopes**: `accounting.contacts accounting.transactions`
- **Token Management**: Automatic refresh handled by modules

### Key Endpoints Used
- `GET /Contacts` - Search and retrieve contacts
- `POST /Contacts` - Create new contacts
- `PUT /ContactGroups/{id}/Contacts` - Manage contact groups
- `GET /Invoices` - Search invoices by contact and date
- `POST /Invoices/{id}` - Update invoice contact assignment
- `GET /RepeatingInvoices` - Search repeating invoice templates
- `POST /RepeatingInvoices` - Create new repeating templates

### Rate Limiting
- Automatic retry logic for rate-limited requests
- Efficient batch processing for multiple operations
- Optimized API queries using recommended parameters

## 🔧 Troubleshooting

### Common Issues

#### Authentication Failures
```
Error: "Failed to authenticate with Xero"
```
**Solutions**:
- Verify `XERO_CLIENT_ID` and `XERO_CLIENT_SECRET` in `.env`
- Ensure Custom Connection app is active in Xero Developer Portal
- Check that required scopes are configured

#### Contact Not Found
```
Error: "No contact found with that account number"
```
**Solutions**:
- Verify account number format (ABC001234 or ABC001234/XX)
- Try searching with just the 8-character property base
- Use debug mode to test specific contact IDs

#### Balance Check Failures
```
Error: "Failed to get contact balance"
```
**Solutions**:
- Ensure contact has transaction history
- Check that contact is not archived in Xero
- Verify API permissions include `accounting.transactions`

#### Group Assignment Issues
```
Warning: "Previous accounts still due group not found"
```
**Solutions**:
- Create the contact group manually in Xero
- Ensure exact spelling: "Previous accounts still due"
- Check contact group permissions in Xero

### Debug Mode
Enable debug mode in sidebar for:
- Testing invoice search with known contact IDs
- Verifying API connectivity
- Troubleshooting specific account numbers

### Logging
All operations are logged to console with detailed information:
- API request/response details
- Business logic decisions
- Error messages with context

## 🚧 Known Limitations

1. **Single Tenant**: Currently supports one Xero organization per deployment
2. **Contact Group Dependency**: Requires "Previous accounts still due" group to exist
3. **Manual Verification**: Some operations may require manual verification in Xero
4. **Custom Connection Only**: Designed for Xero Custom Connection apps

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Install development dependencies
4. Make changes and test thoroughly
5. Submit pull request

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable names
- Include docstrings for all functions
- Add type hints where appropriate

### Testing
- Test all modules individually
- Verify complete workflow end-to-end
- Test error conditions and edge cases
- Validate with different contact types and scenarios

## 📞 Support

### Getting Help
- Check troubleshooting section above
- Review console logs for detailed error information
- Test with debug mode enabled
- Verify Xero API connectivity separately

### Reporting Issues
When reporting issues, please include:
- Error messages from console
- Steps to reproduce
- Account number formats being tested
- Xero organization setup details (without sensitive data)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Xero API Team** - For comprehensive API documentation
- **Streamlit Community** - For the excellent web framework
- **Property Management Industry** - For workflow requirements and testing

---


*Last updated: July 2025*