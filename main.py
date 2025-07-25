#!/usr/bin/env python3
"""
Main orchestration script that runs the complete AI Link candidate pipeline:
1. Fetch new candidates from Lever API
2. Filter candidates to essential fields with LinkedIn URLs
3. Sync filtered candidates to Google Sheet with deduplication
"""

import subprocess
import sys
import time
from pathlib import Path

def run_script(script_name: str, description: str) -> bool:
    """
    Run a Python script and handle errors
    
    Args:
        script_name: Name of the script to run
        description: Description of what the script does
        
    Returns:
        True if successful, False if failed
    """
    print(f"\n🚀 {description}")
    print("=" * 60)
    
    script_path = Path(script_name)
    if not script_path.exists():
        print(f"❌ Script not found: {script_name}")
        return False
    
    try:
        # Run the script and capture output
        result = subprocess.run([
            sys.executable, script_name
        ], capture_output=True, text=True, timeout=1800)  # 30 minute timeout
        
        # Print the output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("⚠️  Stderr:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully!")
            return True
        else:
            print(f"❌ {description} failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timed out after 30 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False

def main():
    """Main orchestration function"""
    print("🎯 AI Link Candidate Pipeline")
    print("=" * 60)
    print("Complete automation: Lever API → Filter → Google Sheets")
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Fetch candidates from Lever API
    step1_success = run_script(
        "get_candidates_from_opportunity.py",
        "Step 1: Fetching candidates from Lever API"
    )
    
    if not step1_success:
        print("\n❌ Pipeline failed at Step 1 - Cannot continue without candidate data")
        return
    
    # Check if the JSON file was created
    candidates_file = Path("ai_link_email_list_candidates.json")
    if not candidates_file.exists():
        print(f"\n❌ Expected output file not found: {candidates_file}")
        return
    
    print(f"✅ Step 1 output verified: {candidates_file}")
    
    # Step 2: Filter candidates and get LinkedIn URLs
    step2_success = run_script(
        "filter_candidates_with_linkedin.py", 
        "Step 2: Filtering candidates and fetching LinkedIn URLs"
    )
    
    if not step2_success:
        print("\n❌ Pipeline failed at Step 2 - Cannot continue without filtered data")
        return
    
    # Check if the filtered JSON file was created
    filtered_file = Path("filtered_candidates_with_linkedin.json")
    if not filtered_file.exists():
        print(f"\n❌ Expected filtered file not found: {filtered_file}")
        return
    
    print(f"✅ Step 2 output verified: {filtered_file}")
    
    # Step 3: Sync candidates to Google Sheet
    step3_success = run_script(
        "sync_sheet_with_candidates.py",
        "Step 3: Syncing candidates to Google Sheet with deduplication"
    )
    
    if not step3_success:
        print("\n❌ Pipeline failed at Step 3 - Sheet sync failed")
        return
    
    # Pipeline completed successfully
    print("\n" + "=" * 60)
    print("🎉 AI Link Candidate Pipeline Completed Successfully!")
    print("=" * 60)
    print(f"✅ Step 1: Lever API data fetched")
    print(f"✅ Step 2: Candidates filtered with LinkedIn URLs")  
    print(f"✅ Step 3: Google Sheet updated with new candidates")
    print(f"Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show file summary
    try:
        import json
        
        # Load and show summary of processed data
        with open(candidates_file, 'r') as f:
            raw_candidates = json.load(f)
        
        with open(filtered_file, 'r') as f:
            filtered_candidates = json.load(f)
        
        print(f"\n📊 Processing Summary:")
        print(f"   • Raw candidates from Lever: {len(raw_candidates)}")
        print(f"   • Filtered candidates with LinkedIn: {len(filtered_candidates)}")
        print(f"   • LinkedIn success rate: {len([c for c in filtered_candidates if c.get('linkedin_url')])}/{len(filtered_candidates)}")
        
    except Exception as e:
        print(f"⚠️  Could not load summary data: {e}")
    
    print(f"\n🔗 Files created:")
    print(f"   • {candidates_file}")
    print(f"   • {filtered_file}")
    print(f"\n📋 Next steps: Check your Google Sheet for new candidates!")

if __name__ == "__main__":
    main()