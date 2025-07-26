#!/usr/bin/env python3
"""
Sheet sync script that reads from Google Sheet and adds new candidates with email deduplication
"""

import os
import json
import datetime
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("❌ Required packages not installed. Run: pip install gspread google-auth")
    exit(1)

def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def extract_linkedin_username(linkedin_url: str) -> Optional[str]:
    """
    Extract LinkedIn username from various LinkedIn URL formats
    
    Examples:
    - http://www.linkedin.com/in/artoyer → artoyer
    - https://linkedin.com/in/artoyer/ → artoyer  
    - https://www.linkedin.com/in/artoyer/details/experience/ → artoyer
    
    Args:
        linkedin_url: Full LinkedIn URL
        
    Returns:
        LinkedIn username if found, None otherwise
    """
    if not linkedin_url:
        return None
    
    # Pattern to extract username from /in/username/ or /in/username
    # Handles various formats and ignores anything after the username
    pattern = r'linkedin\.com/in/([^/?]+)'
    
    match = re.search(pattern, linkedin_url, re.IGNORECASE)
    if match:
        username = match.group(1).strip()
        # Remove any trailing characters that might have been included
        username = re.sub(r'[^a-zA-Z0-9\-_].*$', '', username)
        return username.lower() if username else None
    
    return None

def split_name(full_name: str) -> Tuple[str, str]:
    """
    Split full name into first and last name
    
    Args:
        full_name: Full name string
        
    Returns:
        Tuple of (first_name, last_name)
    """
    if not full_name:
        return "", ""
    
    name_parts = full_name.strip().split()
    if len(name_parts) == 0:
        return "", ""
    elif len(name_parts) == 1:
        return name_parts[0], ""
    else:
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:])
        return first_name, last_name

def distribute_emails(all_emails: List[str], column_mapping: Dict[str, int], num_columns: int) -> Dict[str, str]:
    """
    Distribute candidate emails across available email columns
    
    Args:
        all_emails: List of email addresses from candidate
        column_mapping: Dictionary mapping field names to column indices
        num_columns: Total number of columns in the sheet
        
    Returns:
        Dictionary mapping column indices to email values
    """
    email_distribution = {}
    
    if not all_emails:
        return email_distribution
    
    # Available email columns in order of preference
    email_columns = [
        ('email', column_mapping.get('email')),          # Primary email column (E)
        ('email_2', 5),                                  # Column F (index 5)
        ('email_3', 6)                                   # Column G (index 6)
    ]
    
    # Distribute emails across available columns
    email_index = 0
    for field_name, col_index in email_columns:
        if email_index < len(all_emails) and col_index is not None and col_index < num_columns:
            email_distribution[col_index] = all_emails[email_index]
            email_index += 1
    
    return email_distribution

def format_today_date() -> str:
    """
    Format today's date as M/D/YY
    
    Returns:
        Today's date in M/D/YY format (e.g., "1/24/25")
    """
    today = datetime.date.today()
    return f"{today.month}/{today.day}/{today.year % 100:02d}"

class SheetSync:
    def __init__(self, credentials_file: str, spreadsheet_id: str):
        """
        Initialize Sheet Sync manager
        
        Args:
            credentials_file: Path to Google service account credentials JSON
            spreadsheet_id: ID of the target Google Spreadsheet
        """
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.client = None
        self.sheet = None
        self.worksheet = None
        
    def authenticate(self) -> bool:
        """Authenticate with Google Sheets API"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=scope
            )
            self.client = gspread.authorize(creds)
            print("✅ Successfully authenticated with Google Sheets API")
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def open_spreadsheet(self, worksheet_name: str = None) -> bool:
        """
        Open the spreadsheet and worksheet
        
        Args:
            worksheet_name: Name of the worksheet tab (uses first sheet if None)
        """
        try:
            self.sheet = self.client.open_by_key(self.spreadsheet_id)
            
            if worksheet_name:
                self.worksheet = self.sheet.worksheet(worksheet_name)
            else:
                # Use the first worksheet
                self.worksheet = self.sheet.get_worksheet(0)
            
            print(f"✅ Opened spreadsheet: {self.sheet.title}")
            print(f"✅ Using worksheet: {self.worksheet.title}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to open spreadsheet '{self.spreadsheet_id}': {e}")
            return False
    
    def get_sheet_structure(self) -> Tuple[Set[str], Set[str], Set[str], Dict[str, int]]:
        """
        Get existing emails, names, LinkedIn URLs, and column mapping from the sheet
        
        Returns:
            Tuple of (existing_emails_set, existing_names_set, existing_linkedin_urls_set, column_mapping_dict)
        """
        try:
            all_values = self.worksheet.get_all_values()
            
            if not all_values:
                print("⚠️  Sheet appears to be empty")
                return set(), set(), set(), {}
            
            # Get headers and create column mapping
            headers = all_values[0]
            column_mapping = {}
            
            print(f"📋 Sheet headers: {headers}")
            
            # Direct column mapping for your specific sheet structure
            # Data placement: D=first_name, E=last_name, F=email, J=location, L=linkedin_url, S=join_date
            expected_columns = {
                'first_name': 2,   # Column C (0-indexed = 2) - for data placement
                'last_name': 3,    # Column D (0-indexed = 3) - for data placement
                'email': 4,        # Column E (0-indexed = 4) - for data placement
                'location': 8,     # Column I (0-indexed = 8) - for data placement
                'linkedin_url': 10, # Column K (0-indexed = 10) - for data placement
                'join_date': 17    # Column R (0-indexed = 17) - for data placement
            }
            
            print(f"🎯 Using column mapping for data placement:")
            print(f"   first_name → Column C (index 2)")
            print(f"   last_name → Column D (index 3)")
            print(f"   email → Column E (index 4)")
            print(f"   location → Column I (index 8)")
            print(f"   linkedin_url → Column K (index 10)")
            print(f"   join_date → Column R (index 17)")
            
            # Verify the expected columns exist and map them
            for field, col_index in expected_columns.items():
                if col_index < len(headers):
                    column_mapping[field] = col_index
                    print(f"✅ Mapped {field} to column {col_index} ({chr(65+col_index)}: {headers[col_index] if headers[col_index] else 'Empty'})")
                else:
                    print(f"⚠️  Column {col_index} ({chr(65+col_index)}) not found for {field}")
            
            # Also try flexible mapping as backup
            field_mappings = {
                'first_name': ['first_name', 'first name', 'firstname'],
                'last_name': ['last_name', 'last name', 'lastname'],
                'email': ['email address', 'email', 'e-mail'],
                'location': ['location', 'city', 'address'],
                'linkedin_url': ['linkedin_url', 'linkedin url', 'linkedin', 'social'],
                'join_date': ['join date', 'date', 'created', 'added']
            }
            
            # Only use flexible mapping if direct mapping didn't work
            for field, possible_headers in field_mappings.items():
                if field not in column_mapping:  # Only if not already mapped
                    for i, header in enumerate(headers):
                        header_lower = header.lower().strip()
                        if any(possible in header_lower for possible in possible_headers):
                            column_mapping[field] = i
                            print(f"✅ Backup mapped {field} to column {i} ({header})")
                            break
            
            # Find emails from multiple columns for deduplication - columns F, G, H (indices 5, 6, 7)
            email_columns = [5, 6, 7]  # Column F, G, H for checking existing emails
            emails = set()
            
            print(f"📧 Checking for existing emails in columns F, G, H (indices 5, 6, 7)")
            
            # Find existing names and LinkedIn URLs by searching for actual header names
            existing_names = set()
            existing_linkedin_urls = set()
            first_name_col = None
            last_name_col = None
            linkedin_url_col = None
            
            # Find columns by header names
            for i, header in enumerate(headers):
                header_lower = header.lower().strip()
                if header_lower == 'first_name':
                    first_name_col = i
                elif header_lower == 'last_name':
                    last_name_col = i
                elif header_lower == 'linkedin_url':
                    linkedin_url_col = i
            
            # Display column information
            if first_name_col is not None and last_name_col is not None:
                print(f"👤 Checking for existing names in columns {chr(65+first_name_col)} ({first_name_col}), {chr(65+last_name_col)} ({last_name_col})")
                print(f"   Headers: '{headers[first_name_col]}', '{headers[last_name_col]}'")
            
            if linkedin_url_col is not None:
                print(f"🔗 Checking for existing LinkedIn URLs in column {chr(65+linkedin_url_col)} ({linkedin_url_col})")
                print(f"   Header: '{headers[linkedin_url_col]}'")
            else:
                print("⚠️  Could not find 'linkedin_url' header column for LinkedIn URL checking")
                
            if all_values:
                for row in all_values[1:]:  # Skip header row
                    # Collect emails
                    for col_index in email_columns:
                        if len(row) > col_index and row[col_index]:
                            email_value = row[col_index].lower().strip()
                            if email_value:  # Only add non-empty emails
                                emails.add(email_value)
                    
                    # Collect names - combine first and last name using header-found columns
                    if first_name_col is not None and last_name_col is not None:
                        first_name = ""
                        last_name = ""
                        if len(row) > first_name_col and row[first_name_col]:
                            first_name = row[first_name_col].strip()
                        if len(row) > last_name_col and row[last_name_col]:
                            last_name = row[last_name_col].strip()
                        
                        # Create full name for comparison
                        if first_name or last_name:
                            full_name = f"{first_name} {last_name}".strip().lower()
                            if full_name:
                                existing_names.add(full_name)
                    
                    # Collect LinkedIn usernames
                    if linkedin_url_col is not None:
                        if len(row) > linkedin_url_col and row[linkedin_url_col]:
                            linkedin_url = row[linkedin_url_col].strip()
                            if linkedin_url:
                                # Extract username from LinkedIn URL for better duplicate detection
                                linkedin_username = extract_linkedin_username(linkedin_url)
                                if linkedin_username:
                                    existing_linkedin_urls.add(linkedin_username)
            else:
                # Still collect emails even if name columns not found
                if all_values:
                    for row in all_values[1:]:  # Skip header row, still collect emails and LinkedIn URLs
                        for col_index in email_columns:
                            if len(row) > col_index and row[col_index]:
                                email_value = row[col_index].lower().strip()
                                if email_value:  # Only add non-empty emails
                                    emails.add(email_value)
                        
                        # Still collect LinkedIn usernames even if name columns not found
                        if linkedin_url_col is not None:
                            if len(row) > linkedin_url_col and row[linkedin_url_col]:
                                linkedin_url = row[linkedin_url_col].strip()
                                if linkedin_url:
                                    # Extract username from LinkedIn URL for better duplicate detection
                                    linkedin_username = extract_linkedin_username(linkedin_url)
                                    if linkedin_username:
                                        existing_linkedin_urls.add(linkedin_username)
                
            print(f"📊 Found {len(emails)} existing email addresses across columns F, G, H")
            print(f"📊 Found {len(existing_names)} existing names")
            print(f"📊 Found {len(existing_linkedin_urls)} existing LinkedIn usernames")
            
            # Show sample of existing names for debugging
            if existing_names:
                sample_names = list(existing_names)[:5]
                print(f"   Sample existing names: {sample_names}")
                
                # Show breakdown by column
                for col_index in email_columns:
                    col_letter = chr(65 + col_index)
                    col_emails = set()
                    for row in all_values[1:]:
                        if len(row) > col_index and row[col_index]:
                            email_value = row[col_index].lower().strip()
                            if email_value:
                                col_emails.add(email_value)
                    print(f"   • Column {col_letter}: {len(col_emails)} emails")
            else:
                print("⚠️  Could not find email columns for deduplication")
            
            return emails, existing_names, existing_linkedin_urls, column_mapping
            
        except Exception as e:
            print(f"⚠️  Could not fetch sheet structure: {e}")
            return set(), set(), set(), {}
    
    def add_new_candidates(self, candidates: List[Dict]) -> int:
        """
        Add new candidates to the sheet (avoiding duplicates) with proper column mapping
        
        Args:
            candidates: List of candidate dictionaries with name, email, location, linkedin_url
            
        Returns:
            Number of new candidates added
        """
        if not candidates:
            print("⚠️  No candidates to process")
            return 0
        
        # Get sheet structure, existing emails, names, and LinkedIn URLs
        existing_emails, existing_names, existing_linkedin_urls, column_mapping = self.get_sheet_structure()
        
        if not column_mapping:
            print("❌ Could not determine sheet column structure")
            return 0
        
        # Filter out duplicates by checking ALL candidate emails and names against existing sheet data
        new_candidates = []
        duplicates_count = 0
        
        for candidate in candidates:
            all_emails = candidate.get('all_emails', [])
            candidate_name = candidate.get('name', '').strip()
            
            if not all_emails:
                # Skip candidates without any email addresses
                duplicates_count += 1
                print(f"   ⚠️  Skipping {candidate_name or 'Unknown'} - no email addresses")
                continue
            
            # Check if ANY of the candidate's emails already exist in the sheet
            is_duplicate = False
            duplicate_reason = ""
            candidate_emails = [email.lower().strip() for email in all_emails if email]
            
            # Check email duplicates
            for candidate_email in candidate_emails:
                if candidate_email in existing_emails:
                    is_duplicate = True
                    duplicate_reason = f"email '{candidate_email}' already exists"
                    break
            
            # Check name duplicates if not already a duplicate
            if not is_duplicate and candidate_name:
                candidate_name_lower = candidate_name.lower().strip()
                if candidate_name_lower in existing_names:
                    is_duplicate = True
                    duplicate_reason = f"name '{candidate_name}' already exists"
            
            # Check LinkedIn URL duplicates if not already a duplicate
            if not is_duplicate:
                candidate_linkedin_url = candidate.get('linkedin_url', '').strip()
                if candidate_linkedin_url:
                    # Extract username from candidate's LinkedIn URL
                    candidate_linkedin_username = extract_linkedin_username(candidate_linkedin_url)
                    if candidate_linkedin_username and candidate_linkedin_username in existing_linkedin_urls:
                        is_duplicate = True
                        duplicate_reason = f"LinkedIn username '{candidate_linkedin_username}' already exists"
            
            if not is_duplicate:
                new_candidates.append(candidate)
                print(f"   ✅ New candidate: {candidate_name or 'Unknown'} - {len(candidate_emails)} email(s)")
            else:
                duplicates_count += 1
                print(f"   🔍 Duplicate found: {candidate_name or 'Unknown'} - {duplicate_reason}")
        
        if not new_candidates:
            print(f"✅ No new candidates to add - {duplicates_count} duplicates found")
            return 0
        
        print(f"📊 Processing {len(new_candidates)} new candidates ({duplicates_count} duplicates skipped)")
        
        # Determine the number of columns in the sheet
        all_values = self.worksheet.get_all_values()
        num_columns = len(all_values[0]) if all_values else 6
        
        # Prepare rows for batch update
        rows_to_add = []
        today_date = format_today_date()
        
        for candidate in new_candidates:
            # Create row with correct number of columns (filled with empty strings)
            row = [''] * num_columns
            
            # Split name into first and last
            first_name, last_name = split_name(candidate.get('name', ''))
            
            # Map basic data to correct columns
            if 'first_name' in column_mapping:
                row[column_mapping['first_name']] = first_name
            if 'last_name' in column_mapping:
                row[column_mapping['last_name']] = last_name
            if 'location' in column_mapping:
                row[column_mapping['location']] = candidate.get('location', '')
            if 'linkedin_url' in column_mapping:
                row[column_mapping['linkedin_url']] = candidate.get('linkedin_url', '')
            if 'join_date' in column_mapping:
                row[column_mapping['join_date']] = today_date
            
            # Distribute multiple emails across available columns
            all_emails = candidate.get('all_emails', [])
            email_distribution = distribute_emails(all_emails, column_mapping, num_columns)
            
            # Apply email distribution to the row
            for col_index, email_value in email_distribution.items():
                if col_index < num_columns:
                    row[col_index] = email_value
            
            rows_to_add.append(row)
            
        # Debug: Show first row mapping and email distribution
        if rows_to_add:
            sample_candidate = new_candidates[0]
            sample_emails = sample_candidate.get('all_emails', [])
            sample_distribution = distribute_emails(sample_emails, column_mapping, num_columns)
            
            print(f"🐛 Sample row mapping: {rows_to_add[0]}")
            print(f"🐛 Sample email distribution: {sample_distribution}")
            print(f"🐛 Sample candidate emails: {sample_emails}")
        
        # Add rows to sheet
        try:
            self.worksheet.append_rows(rows_to_add)
            print(f"✅ Successfully added {len(new_candidates)} new candidates")
            return len(new_candidates)
            
        except Exception as e:
            print(f"❌ Failed to add candidates to sheet: {e}")
            return 0

def main():
    """Main function to sync candidates with Google Sheet"""
    print("🚀 Sheet Sync with Email Deduplication")
    print("=" * 50)
    
    # Load environment variables
    load_env_file()
    
    # Configuration
    credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    spreadsheet_id = os.getenv('TARGET_SPREADSHEET_ID')
    
    # Check configuration
    if not Path(credentials_file).exists():
        print(f"❌ Google credentials file not found: {credentials_file}")
        return
    
    if not spreadsheet_id:
        print("❌ TARGET_SPREADSHEET_ID environment variable not set")
        return
    
    # Check if filtered candidates file exists
    candidates_file = Path("filtered_candidates_with_linkedin.json")
    if not candidates_file.exists():
        print(f"❌ Filtered candidates file not found: {candidates_file}")
        print("Please run filter_candidates_with_linkedin.py first")
        return
    
    # Load candidates data
    print("📂 Loading filtered candidates...")
    try:
        with open(candidates_file, 'r') as f:
            candidates = json.load(f)
        print(f"✅ Loaded {len(candidates)} candidates from file")
    except Exception as e:
        print(f"❌ Failed to load candidates file: {e}")
        return
    
    # Initialize sheet sync
    sync_manager = SheetSync(credentials_file, spreadsheet_id)
    
    # Authenticate
    if not sync_manager.authenticate():
        return
    
    # Open spreadsheet
    if not sync_manager.open_spreadsheet():
        return
    
    # Add new candidates
    print(f"\n📊 Syncing candidates to sheet...")
    new_count = sync_manager.add_new_candidates(candidates)
    
    # Summary
    print(f"\n📈 Sync Summary:")
    print(f"   • Total candidates processed: {len(candidates)}")
    print(f"   • New candidates added: {new_count}")
    print(f"   • Duplicates skipped: {len(candidates) - new_count}")
    print(f"   • Join date format: {format_today_date()}")
    print(f"   • Target sheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    
    if new_count > 0:
        print("\n✅ Sheet sync completed successfully!")
    else:
        print("\nℹ️  No new candidates added - all emails already exist in sheet")

if __name__ == "__main__":
    main()