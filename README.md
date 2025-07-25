# AI Link Google Sheets Integration

This application updates a Google Sheet with new applicants from the AI Link email list using the Lever API.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Lever API:**
   - Create a `.env` file with your Lever API key:
   ```
   LEVER_API_KEY=your_lever_api_key_here
   ```

3. **Setup Google Sheets API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create or select a project
   - Enable the Google Sheets API and Google Drive API
   - Create a Service Account and download the credentials JSON file
   - Save the credentials as `credentials.json` in this directory
   - Share your Google Spreadsheet with the service account email

4. **Configure Google Sheets:**
   - Create or use existing Google Spreadsheet
   - Set environment variables (optional):
   ```
   GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
   GOOGLE_SPREADSHEET_NAME=Your Spreadsheet Name
   ```

## Usage

### Fetch candidates from Lever API only:
```bash
python get_candidates_from_opportunity.py
```

### Update Google Sheets with latest candidates:
```bash
python update_google_sheet.py
```

## Features

- Fetches candidates from "AI Link Email List" opportunity in Lever
- Automatically creates Google Sheets with proper headers
- Identifies new candidates and adds them to the sheet
- Updates existing candidates with latest information
- Handles rate limiting and error recovery
- Maintains sync timestamps and status tracking

## Sheet Columns

The Google Sheet includes these columns:
- Name, Email, Location, Headline
- Stage, Origin, Created Date, Updated Date
- Archived status, Candidate ID, Posting Title
- Applications Count, Last Sync, Status, Notes# ai-link
