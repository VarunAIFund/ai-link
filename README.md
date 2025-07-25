# AI Link Candidate Pipeline 🚀

This application automatically syncs candidates from Lever API to Google Sheets with LinkedIn URL enrichment and smart duplicate detection. Perfect for managing AI Link email list candidates!

## 📋 What This Application Does

1. **Fetches candidates** from your "AI Link Email List" opportunity in Lever
2. **Enriches data** by extracting LinkedIn URLs and collecting all email addresses
3. **Syncs to Google Sheets** while preventing duplicates (by email, name, or LinkedIn URL)
4. **Incremental processing** - only processes new/updated candidates on subsequent runs

## 🛠️ Prerequisites

Before you start, make sure you have:

- **Python 3.7+** installed on your computer
- **Git** installed ([Download here](https://git-scm.com/downloads))
- **Lever API access** with an API key
- **Google account** with access to Google Sheets
- **Command line/Terminal** basic knowledge

## 💻 Step-by-Step Installation

### 1. Open Command Line/Terminal

**On Windows:**
- Press `Windows + R`, type `cmd`, press Enter

**On Mac:**
- Press `Cmd + Space`, type "Terminal", press Enter

**On Linux:**
- Press `Ctrl + Alt + T`

### 2. Navigate to Your Desktop

```bash
cd Desktop
```

### 3. Clone the Repository

```bash
git clone https://github.com/VarunAIFund/ai-link.git
```

### 4. Enter the Project Directory

```bash
cd ai-link
```

### 5. Install Python Dependencies

```bash
pip install -r requirements.txt
```

If you get a "pip not found" error, try:
```bash
pip3 install -r requirements.txt
```

## 🔑 Configuration Setup

### Step 1: Get Your Lever API Key

1. Log into your Lever account
2. Go to Settings → Integrations → API
3. Create or copy your API key

### Step 2: Create Environment File

Create a file called `.env` in the project folder with your API key:

```bash
# On Mac/Linux:
touch .env

# On Windows:
type nul > .env
```

Open the `.env` file in any text editor and add:
```
LEVER_API_KEY=your_actual_api_key_here
TARGET_SPREADSHEET_ID=your_google_sheet_id_here
```

### Step 3: Setup Google Sheets API

1. **Go to Google Cloud Console:**
   - Visit [console.cloud.google.com](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable APIs:**
   - Search for "Google Sheets API" and enable it
   - Search for "Google Drive API" and enable it

3. **Create Service Account:**
   - Go to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Give it a name like "AI Link Sheet Sync"
   - Click "Create and Continue"
   - Skip the roles section, click "Done"

4. **Download Credentials:**
   - Click on your newly created service account
   - Go to "Keys" tab
   - Click "Add Key" → "Create New Key"
   - Choose "JSON" format
   - Download the file and save it as `credentials.json` in your project folder

### Step 4: Setup Your Google Sheet

1. **Create or open your Google Sheet**
2. **Get the Sheet ID:**
   - Copy the URL of your sheet
   - The ID is the long string between `/spreadsheets/d/` and `/edit`
   - Example: `1dWQ6fxXLXA4txUgEJFdogErLB55ycbWamOITehRB8LY`
   - Add this ID to your `.env` file as `TARGET_SPREADSHEET_ID`

3. **Share the sheet:**
   - Open your `credentials.json` file
   - Find the "client_email" field (looks like: `something@project-name.iam.gserviceaccount.com`)
   - Share your Google Sheet with this email address (give it "Editor" permissions)

## 🚀 How to Run

### Run the Complete Pipeline

```bash
python main.py
```

This runs all 3 steps automatically:
1. ✅ Fetches candidates from Lever API
2. ✅ Enriches with LinkedIn URLs and emails
3. ✅ Syncs to Google Sheet with duplicate detection

### Run Individual Steps (Advanced)

```bash
# Step 1 only: Fetch candidates
python get_candidates_from_opportunity.py

# Step 2 only: Add LinkedIn URLs
python filter_candidates_with_linkedin.py

# Step 3 only: Sync to Google Sheets
python sync_sheet_with_candidates.py
```

## 📊 What Happens When You Run It

### First Run:
```
🚀 AI Link Candidate Pipeline
==================================================
Step 1: Fetching candidates from Lever API
✅ Successfully fetched 150 candidates from Lever API
📊 Processing Summary:
   • New candidates: 150
   • Updated candidates: 0
   • Preserved candidates: 0

Step 2: Filtering candidates and fetching LinkedIn URLs
🔍 Processing 150 unprocessed candidates...
✅ LinkedIn URLs found for 89 candidates
✅ All emails collected for 150 candidates

Step 3: Syncing candidates to Google Sheet
📧 Checking for existing emails in columns F, G, H
👤 Checking for existing names in columns D, E
🔗 Checking for existing LinkedIn URLs in column L
✅ Successfully added 145 new candidates (5 duplicates skipped)

🎉 AI Link Candidate Pipeline Completed Successfully!
```

### Subsequent Runs:
```
Step 1: Fetching candidates from Lever API
✅ Successfully fetched 155 candidates from Lever API
📊 Processing Summary:
   • New candidates: 5
   • Updated candidates: 2
   • Preserved candidates: 148

Step 2: Only processing 7 new/updated candidates...
✅ No new or updated candidates found - all candidates up to date
```

## 📁 Files Created

After running, you'll see these files in your folder:
- `ai_link_email_list_candidates.json` - Raw candidate data from Lever
- `filtered_candidates_with_linkedin.json` - Processed candidates with LinkedIn URLs

## 🔄 Incremental Processing

This application is smart about not doing duplicate work:

- **First run:** Processes all candidates
- **Subsequent runs:** Only processes new or updated candidates
- **API efficiency:** Avoids redundant LinkedIn URL lookups
- **Resume capability:** Safe to stop and restart at any time

## 🛠️ Troubleshooting

### "ModuleNotFoundError" Error
```bash
pip install -r requirements.txt
# Or try:
pip3 install -r requirements.txt
```

### "LEVER_API_KEY not set" Error
- Check your `.env` file exists in the project folder
- Make sure it contains: `LEVER_API_KEY=your_actual_key`
- No spaces around the equals sign

### "Permission denied" Google Sheets Error
- Make sure you shared your Google Sheet with the service account email
- Check the `client_email` in your `credentials.json` file
- Give it "Editor" permissions

### "No candidates found" Error
- Check your Lever API key has access to the "AI Link Email List" opportunity
- Verify the opportunity name exists in your Lever account

### "Authentication failed" Error
- Check your `credentials.json` file is in the project folder
- Make sure the Google Sheets API and Google Drive API are enabled
- Verify your service account has the correct permissions

## 📚 How It Works

1. **Step 1:** Connects to Lever API and fetches all candidates from "AI Link Email List"
2. **Step 2:** For each candidate, makes additional API calls to get detailed profiles and extract LinkedIn URLs
3. **Step 3:** Checks Google Sheet for duplicates (by email, name, LinkedIn URL) and adds only new candidates

## 🔒 Security Note

Never commit these files to Git (they're in `.gitignore`):
- `.env` (contains your API keys)
- `credentials.json` (contains Google API credentials)
- `*.json` data files (contain personal candidate information)

## 🆘 Need Help?

If you run into issues:
1. Check the troubleshooting section above
2. Make sure all prerequisites are installed
3. Verify your API keys and permissions are correct
4. Check that your Google Sheet exists and is shared properly

---

**Happy candidate syncing!** 🎉