#!/usr/bin/env python3
"""
Lever API script to get all candidates from opportunities
"""

import os
import json
import requests
import time
from pathlib import Path
from typing import List, Dict, Optional

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

load_env_file()

class LeverAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.lever.co/v1"
        self.session = requests.Session()
        self.session.auth = (api_key, '')
        self.rate_limit_delay = 0.6

    def make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make API request with rate limiting and error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error making request to {endpoint}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text[:500]}")
            return {}

def find_posting_by_title(api: LeverAPI, title: str) -> Optional[str]:
    """
    Find a posting ID by its title
    
    Args:
        api: LeverAPI instance
        title: Title of the posting to find
        
    Returns:
        Posting ID if found, None otherwise
    """
    print(f"🔍 Searching for posting with title: '{title}'...")
    
    next_token = None
    while True:
        params = {"limit": 100}
        if next_token:
            params["offset"] = next_token
            
        postings_data = api.make_request("/postings", params)
        
        if not postings_data or 'data' not in postings_data:
            break
            
        postings = postings_data['data']
        
        for posting in postings:
            posting_title = posting.get('text', '')
            if title.lower() in posting_title.lower():
                print(f"✅ Found posting: '{posting_title}' (ID: {posting['id']})")
                return posting['id']
        
        next_token = postings_data.get('next')
        if not next_token:
            break
    
    print(f"❌ Posting with title '{title}' not found")
    return None

def load_existing_candidates(output_file: Path) -> Dict[str, Dict]:
    """
    Load existing candidates from file and create lookup by candidate_id
    
    Args:
        output_file: Path to the existing candidates JSON file
        
    Returns:
        Dictionary mapping candidate_id to candidate data
    """
    if not output_file.exists():
        print("📝 No existing candidates file found - will create new one")
        return {}
    
    try:
        with open(output_file, 'r') as f:
            existing_candidates = json.load(f)
        
        # Create lookup dictionary by candidate_id
        candidate_lookup = {}
        for candidate in existing_candidates:
            candidate_id = candidate.get('candidate_id')
            if candidate_id:
                candidate_lookup[candidate_id] = candidate
        
        print(f"📊 Loaded {len(candidate_lookup)} existing candidates from file")
        return candidate_lookup
        
    except Exception as e:
        print(f"⚠️  Error loading existing candidates file: {e}")
        print("📝 Will create new file")
        return {}

def merge_candidate_data(existing_candidate: Dict, fresh_candidate: Dict) -> Dict:
    """
    Merge existing candidate data with fresh data from Lever API
    Preserves processing status and enriched data while updating basic Lever fields
    
    Args:
        existing_candidate: Candidate data from existing file (may have already_processed, linkedin_url, etc.)
        fresh_candidate: Fresh candidate data from Lever API
        
    Returns:
        Merged candidate data
    """
    # Start with existing candidate to preserve all enriched fields
    merged = existing_candidate.copy()
    
    # Update basic Lever fields that might have changed
    lever_fields = ['name', 'email', 'location', 'headline', 'stage', 'origin', 'updatedAt', 'archived', 'applications']
    
    for field in lever_fields:
        if field in fresh_candidate:
            merged[field] = fresh_candidate[field]
    
    # Check if candidate was updated in Lever (need to reprocess if significant changes)
    existing_updated = existing_candidate.get('updatedAt', '')
    fresh_updated = fresh_candidate.get('updatedAt', '')
    
    # If updatedAt changed and candidate was already processed, mark for reprocessing
    if (existing_updated != fresh_updated and 
        existing_candidate.get('already_processed', False) and
        fresh_updated > existing_updated):
        print(f"   🔄 Candidate {fresh_candidate.get('name', 'Unknown')} was updated in Lever - marking for reprocessing")
        merged['already_processed'] = False
    
    return merged

def fetch_candidates_from_specific_opportunity(posting_title: str) -> List[Dict]:
    """
    Fetch candidates from a specific opportunity/posting using Lever API
    
    Args:
        posting_title: Title of the posting to get candidates from
        
    Returns:
        List of candidate dictionaries
    """
    lever_api_key = os.getenv('LEVER_API_KEY')
    if not lever_api_key:
        print("❌ Error: LEVER_API_KEY environment variable not set")
        return []
    
    api = LeverAPI(lever_api_key)
    
    print(f"🔍 Fetching candidates from opportunity: '{posting_title}'...")
    
    # Test API connection first
    print("🔌 Testing API connection...")
    test_data = api.make_request("/opportunities", {"limit": 1})
    if not test_data:
        print("❌ Failed to connect to Lever API. Please check your API key and permissions.")
        return []
    
    # Find the posting ID by title
    posting_id = find_posting_by_title(api, posting_title)
    if not posting_id:
        return []
    
    # Fetch candidates filtered by this posting
    all_candidates = []
    batch_size = 100
    next_token = None
    batch_count = 0
    
    while True:
        batch_count += 1
        
        # Fetch candidates from API with cursor-based pagination
        if next_token:
            print(f"📄 Fetching batch {batch_count} with next token...")
        else:
            print(f"📄 Fetching first batch {batch_count}...")
        
        params = {"limit": batch_size, "posting_id": posting_id}
        if next_token:
            params["offset"] = next_token
        
        candidates_data = api.make_request("/opportunities", params)
        
        if not candidates_data or 'data' not in candidates_data:
            print("❌ No more candidates data received")
            break
        
        candidates = candidates_data['data']
        print(f"📊 Processing {len(candidates)} candidates from batch {batch_count}")
        
        # If no more candidates, break
        if not candidates:
            print("⚠️  No more candidates available")
            break
        
        # Add candidates from this batch (they're already filtered by posting_id)
        for candidate in candidates:
            candidate_profile = {
                'candidate_id': candidate['id'],
                'name': candidate.get('name', 'Unknown'),
                'email': candidate.get('emails', [None])[0] if candidate.get('emails') else None,
                'location': candidate.get('location', ''),
                'headline': candidate.get('headline', ''),
                'stage': candidate.get('stage', ''),
                'origin': candidate.get('origin', ''),
                'createdAt': candidate.get('createdAt', ''),
                'updatedAt': candidate.get('updatedAt', ''),
                'archived': candidate.get('archived', {}).get('archivedAt') is not None if candidate.get('archived') else False,
                'applications': candidate.get('applications', []),
                'posting_id': posting_id,
                'posting_title': posting_title
            }
            all_candidates.append(candidate_profile)
        
        print(f"✅ Total candidates for '{posting_title}': {len(all_candidates)}")
        
        # Get next token for pagination
        next_token = candidates_data.get('next')
        
        # If no next token, we've reached the end
        if not next_token:
            print("⚠️  Reached end of candidates (no next token)")
            break
    
    print(f"🎯 Final result: {len(all_candidates)} candidates from '{posting_title}'")
    return all_candidates

def main():
    """Main function to fetch and save candidates from specific opportunity with incremental processing"""
    print("🚀 Fetching Candidates from 'AI Link Email List' Opportunity - Lever API (Incremental)")
    print("=" * 70)
    
    output_file = Path("ai_link_email_list_candidates.json")
    
    # Load existing candidates to preserve processing status
    existing_candidates = load_existing_candidates(output_file)
    
    # Fetch fresh candidates from Lever API
    posting_title = "AI Link Email List"
    fresh_candidates = fetch_candidates_from_specific_opportunity(posting_title)
    
    if not fresh_candidates:
        print("❌ No candidates found for this opportunity")
        return
    
    print(f"✅ Successfully fetched {len(fresh_candidates)} candidates from Lever API")
    
    # Merge existing and fresh data
    final_candidates = []
    new_candidates_count = 0
    updated_candidates_count = 0
    preserved_candidates_count = 0
    
    print(f"\n🔄 Merging candidates with existing data...")
    
    for fresh_candidate in fresh_candidates:
        candidate_id = fresh_candidate.get('candidate_id')
        
        if candidate_id in existing_candidates:
            # Merge existing with fresh data
            merged_candidate = merge_candidate_data(existing_candidates[candidate_id], fresh_candidate)
            final_candidates.append(merged_candidate)
            
            # Check if this was an update
            if (existing_candidates[candidate_id].get('updatedAt', '') != fresh_candidate.get('updatedAt', '')):
                updated_candidates_count += 1
            else:
                preserved_candidates_count += 1
        else:
            # New candidate - add as is with processing flag
            fresh_candidate['already_processed'] = False
            final_candidates.append(fresh_candidate)
            new_candidates_count += 1
    
    print(f"📊 Processing Summary:")
    print(f"   • New candidates: {new_candidates_count}")
    print(f"   • Updated candidates: {updated_candidates_count}")
    print(f"   • Preserved candidates: {preserved_candidates_count}")
    print(f"   • Total candidates: {len(final_candidates)}")
    
    # Save merged results to file
    with open(output_file, 'w') as f:
        json.dump(final_candidates, f, indent=2)
    
    print(f"💾 Results saved to: {output_file}")
    
    # Show a preview of new/updated candidates
    if new_candidates_count > 0 or updated_candidates_count > 0:
        print(f"\n📋 Preview of new/updated candidates:")
        print("=" * 50)
        
        # Find first few new or updated candidates for preview
        preview_candidates = []
        for candidate in final_candidates:
            candidate_id = candidate.get('candidate_id')
            if (candidate_id not in existing_candidates or 
                (candidate_id in existing_candidates and 
                 existing_candidates[candidate_id].get('updatedAt', '') != candidate.get('updatedAt', ''))):
                preview_candidates.append(candidate)
                if len(preview_candidates) >= 3:
                    break
        
        # Display preview candidates
        for i, candidate in enumerate(preview_candidates, 1):
            status = "🆕 NEW" if candidate.get('candidate_id') not in existing_candidates else "🔄 UPDATED"
            processed_status = "✅ Processed" if candidate.get('already_processed') else "⏳ Pending"
            
            print(f"\n{i}. {candidate['name']} ({status})")
            print(f"   📧 Email: {candidate['email'] or 'Not available'}")
            print(f"   📍 Location: {candidate['location'] or 'Not specified'}")
            print(f"   💼 Headline: {candidate['headline'] or 'Not specified'}")
            print(f"   🎯 Stage: {candidate['stage'] or 'Not specified'}")
            print(f"   📅 Updated: {candidate['updatedAt']}")
            print(f"   🔄 Processing: {processed_status}")
            print("-" * 50)
        
        if (new_candidates_count + updated_candidates_count) > 3:
            print(f"\n... and {(new_candidates_count + updated_candidates_count) - 3} more new/updated candidates")
    else:
        print(f"\n✅ No new or updated candidates found - all {len(final_candidates)} candidates are up to date")

if __name__ == "__main__":
    main()