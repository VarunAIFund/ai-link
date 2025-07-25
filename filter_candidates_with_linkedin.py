#!/usr/bin/env python3
"""
Enhanced JSON filter script that extracts name, email, location, and LinkedIn URLs
from AI Link candidates by making individual API calls to get detailed candidate profiles
"""

import os
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Optional

from get_candidates_from_opportunity import LeverAPI, load_env_file

def extract_linkedin_url(links: List) -> Optional[str]:
    """
    Extract LinkedIn URL from candidate's links
    
    Args:
        links: List of link URLs or dictionaries from candidate profile
        
    Returns:
        LinkedIn URL if found, None otherwise
    """
    if not links:
        return None
    
    linkedin_patterns = [
        r'linkedin\.com/in/',
        r'linkedin\.com/pub/',
        r'www\.linkedin\.com/in/',
        r'www\.linkedin\.com/pub/'
    ]
    
    for link in links:
        # Handle both string URLs and dictionary objects
        if isinstance(link, str):
            url = link
        elif isinstance(link, dict):
            url = link.get('url', '')
        else:
            continue
            
        if url:
            for pattern in linkedin_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return url
    
    return None

class CandidateProfileFetcher:
    def __init__(self, api_key: str):
        """Initialize with Lever API"""
        self.api = LeverAPI(api_key)
        self.successful_fetches = 0
        self.failed_fetches = 0
        self.linkedin_found = 0
        
    
    def get_candidate_details(self, candidate_id: str) -> Optional[Dict]:
        """
        Fetch detailed candidate profile from Lever API
        
        Args:
            candidate_id: The candidate's unique ID
            
        Returns:
            Candidate details dictionary or None if failed
        """
        endpoint = f"/candidates/{candidate_id}"
        try:
            candidate_data = self.api.make_request(endpoint)
            if candidate_data and isinstance(candidate_data, dict) and 'data' in candidate_data:
                self.successful_fetches += 1
                return candidate_data['data']
            else:
                self.failed_fetches += 1
                return None
        except Exception as e:
            print(f"⚠️  Failed to fetch candidate {candidate_id}: {e}")
            self.failed_fetches += 1
            return None
    
    def save_raw_candidates(self, candidates: List[Dict], candidates_file: str):
        """
        Save updated raw candidates back to file
        
        Args:
            candidates: List of candidate dictionaries with processing status
            candidates_file: Path to the raw candidates file
        """
        try:
            with open(candidates_file, 'w') as f:
                json.dump(candidates, f, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save raw candidates file: {e}")
    
    def process_candidates(self, candidates_file: str, output_file: str = "filtered_candidates_with_linkedin.json") -> List[Dict]:
        """
        Process candidates using raw file status tracking
        
        Args:
            candidates_file: Path to the JSON file containing raw candidates
            output_file: Path to the filtered candidates output file
            
        Returns:
            List of all filtered candidate dictionaries
        """
        # Load raw candidates data
        with open(candidates_file, 'r') as f:
            raw_candidates = json.load(f)
        
        print(f"📊 Found {len(raw_candidates)} raw candidates from Lever API")
        
        # Filter out candidates that are already processed
        unprocessed_candidates = []
        already_processed_count = 0
        
        for candidate in raw_candidates:
            if candidate.get('already_processed', False):
                already_processed_count += 1
            else:
                unprocessed_candidates.append(candidate)
        
        print(f"📈 Processing Status Summary:")
        print(f"   • Already processed: {already_processed_count}")
        print(f"   • Unprocessed candidates: {len(unprocessed_candidates)}")
        print(f"   • API calls needed: {len(unprocessed_candidates)}")
        
        if not unprocessed_candidates:
            print("✅ No unprocessed candidates found")
        else:
            print(f"\n🔍 Processing {len(unprocessed_candidates)} unprocessed candidates...")
            print("=" * 60)
        
        # Process unprocessed candidates and mark them as processed
        filtered_candidates = []
        
        for i, candidate in enumerate(unprocessed_candidates, 1):
            candidate_id = candidate.get('candidate_id')
            name = candidate.get('name', 'Unknown')
            
            print(f"📄 [{i}/{len(unprocessed_candidates)}] Processing: {name}")
            
            # Get basic info from existing data
            filtered_candidate = {
                'name': name,
                'email': candidate.get('email'),
                'location': candidate.get('location'),
                'linkedin_url': "",  # Empty string instead of None for blank LinkedIn field
                'all_emails': []     # Will store all emails from Lever API
            }
            
            processing_successful = False
            
            # Fetch detailed profile to get LinkedIn URL and emails
            if candidate_id:
                detailed_profile = self.get_candidate_details(candidate_id)
                
                if detailed_profile and isinstance(detailed_profile, dict):
                    processing_successful = True
                    
                    # Look for LinkedIn URL in links
                    links = detailed_profile.get('links', [])
                    linkedin_url = extract_linkedin_url(links)
                    
                    if linkedin_url:
                        filtered_candidate['linkedin_url'] = linkedin_url
                        self.linkedin_found += 1
                        print(f"   ✅ LinkedIn found: {linkedin_url}")
                    else:
                        print(f"   ❌ No LinkedIn URL found")
                    
                    # Get ALL emails from the detailed profile
                    all_emails = detailed_profile.get('emails', [])
                    if all_emails:
                        filtered_candidate['all_emails'] = all_emails
                        print(f"   📧 Found {len(all_emails)} email(s): {', '.join(all_emails[:2])}{'...' if len(all_emails) > 2 else ''}")
                    else:
                        print(f"   📧 No additional emails found")
                else:
                    print(f"   ⚠️  Failed to fetch detailed profile")
            else:
                print(f"   ⚠️  No candidate ID available")
                processing_successful = True  # Mark as processed even without ID
            
            # Mark candidate as processed and store extracted data in raw data
            if processing_successful:
                candidate['already_processed'] = True
                candidate['linkedin_url'] = filtered_candidate['linkedin_url']
                candidate['all_emails'] = filtered_candidate['all_emails']
                self.save_raw_candidates(raw_candidates, candidates_file)
                print(f"   ✅ Marked as processed and saved to file")
            
            filtered_candidates.append(filtered_candidate)
            
            # Progress update every 10 candidates
            if i % 10 == 0 or i == len(unprocessed_candidates):
                print(f"\n📈 Progress: {i}/{len(unprocessed_candidates)} candidates processed")
                print(f"   • Successful API calls: {self.successful_fetches}")
                print(f"   • Failed API calls: {self.failed_fetches}")
                print(f"   • LinkedIn URLs found: {self.linkedin_found}")
                print("-" * 40)
        
        # Generate final filtered output from ALL processed candidates
        all_filtered_candidates = []
        
        # Get all processed candidates (both already processed and newly processed)
        for candidate in raw_candidates:
            if candidate.get('already_processed', False):
                # Extract the desired fields: name, all_emails, location, linkedin_url
                filtered_entry = {
                    'name': candidate.get('name', 'Unknown'),
                    'all_emails': candidate.get('all_emails', []),  # Use all_emails instead of email
                    'location': candidate.get('location', ''),
                    'linkedin_url': candidate.get('linkedin_url', '')
                }
                all_filtered_candidates.append(filtered_entry)
        
        return all_filtered_candidates
    
    def print_summary(self, new_candidates_processed: int, total_in_file: int):
        """Print processing summary"""
        print(f"\n🎯 Processing Summary:")
        print(f"   • New candidates processed: {new_candidates_processed}")
        print(f"   • Successful API calls: {self.successful_fetches}")
        print(f"   • Failed API calls: {self.failed_fetches}")
        print(f"   • LinkedIn URLs found (new): {self.linkedin_found}")
        if new_candidates_processed > 0:
            print(f"   • LinkedIn success rate (new): {(self.linkedin_found/new_candidates_processed)*100:.1f}%")
        print(f"   • Total candidates in final file: {total_in_file}")

def main():
    """Main function to filter candidates and extract LinkedIn URLs"""
    print("🚀 AI Link Candidates LinkedIn Filter")
    print("=" * 50)
    
    # Load environment variables
    load_env_file()
    
    # Check for API key
    lever_api_key = os.getenv('LEVER_API_KEY')
    if not lever_api_key:
        print("❌ Error: LEVER_API_KEY environment variable not set")
        return
    
    # Check if input file exists
    input_file = Path("ai_link_email_list_candidates.json")
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        print("Please run get_candidates_from_opportunity.py first")
        return
    
    # Initialize the fetcher
    fetcher = CandidateProfileFetcher(lever_api_key)
    
    # Process candidates with incremental logic
    try:
        output_file = Path("filtered_candidates_with_linkedin.json")
        all_filtered_candidates = fetcher.process_candidates(input_file, str(output_file))
        
        # Save merged results (existing + new)
        with open(output_file, 'w') as f:
            json.dump(all_filtered_candidates, f, indent=2)
        
        print(f"\n💾 All filtered candidates saved to: {output_file}")
        
        # Print summary
        new_processed = fetcher.successful_fetches + fetcher.failed_fetches
        fetcher.print_summary(new_processed, len(all_filtered_candidates))
        
        # Show sample of results
        print(f"\n📋 Sample Results:")
        print("=" * 30)
        
        for i, candidate in enumerate(all_filtered_candidates[:3], 1):
            print(f"\n{i}. {candidate['name']}")
            
            # Show all emails
            all_emails = candidate.get('all_emails', [])
            if all_emails:
                print(f"   📧 All Emails ({len(all_emails)}): {', '.join(all_emails)}")
            else:
                print(f"   📧 All Emails: None found")
            
            print(f"   📍 Location: {candidate['location'] or 'Not specified'}")
            print(f"   🔗 LinkedIn: {candidate['linkedin_url'] if candidate['linkedin_url'] else 'Not found'}")
        
        if len(all_filtered_candidates) > 3:
            print(f"\n... and {len(all_filtered_candidates) - 3} more candidates")
        
        print(f"\n✅ Processing completed successfully!")
        
    except Exception as e:
        print(f"❌ Error processing candidates: {e}")
        return

if __name__ == "__main__":
    main()