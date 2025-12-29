#!/usr/bin/env python3
"""
Batch scan all user repositories using the Repository Intelligence Scanner
"""

import subprocess
import sys
import os
from pathlib import Path
import json
from datetime import datetime

def scan_repository(repo_url, output_base_dir):
    """Scan a single repository and return results summary"""
    repo_name = repo_url.split('/')[-1]
    output_dir = output_base_dir / repo_name
    
    print(f"\n🔍 Scanning {repo_name}...")
    print(f"   URL: {repo_url}")
    print(f"   Output: {output_dir}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Run the scanner
        cmd = [
            "repo-scanner", "scan", 
            "--url", repo_url, 
            "--output-dir", str(output_dir)
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minute timeout
        )
        
        success = result.returncode == 0
        
        # Try to read the JSON report for summary
        json_report = output_dir / "scan_report.json"
        summary = {"repo_name": repo_name, "url": repo_url, "success": success}
        
        if json_report.exists() and success:
            try:
                with open(json_report, 'r') as f:
                    data = json.load(f)
                    summary.update({
                        "files_analyzed": data.get("structure", {}).get("file_counts", {}).get("total", 0),
                        "deterministic": data.get("determinism_verification", {}).get("determinism_report", {}).get("determinism_status") == "verified"
                    })
            except:
                pass
        
        print(f"   ✅ Success: {success}")
        if "files_analyzed" in summary:
            print(f"   📊 Files analyzed: {summary['files_analyzed']}")
        
        return summary
        
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Timeout after 5 minutes")
        return {"repo_name": repo_name, "url": repo_url, "success": False, "error": "timeout"}
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"repo_name": repo_name, "url": repo_url, "success": False, "error": str(e)}

def main():
    """Main batch scanning function"""
    print("🚀 Repository Intelligence Scanner - Batch Analysis")
    print("=" * 60)
    
    # Read repository URLs
    repos_file = Path("demo_repos.txt")
    if not repos_file.exists():
        print("❌ demo_repos.txt not found!")
        sys.exit(1)
    
    with open(repos_file, 'r') as f:
        repo_urls = [line.strip() for line in f if line.strip()]
    
    print(f"📋 Found {len(repo_urls)} repositories to scan")
    
    # Create output directory
    output_base = Path("batch_scan_results")
    output_base.mkdir(exist_ok=True)
    
    # Scan all repositories
    results = []
    successful_scans = 0
    
    for repo_url in repo_urls:
        result = scan_repository(repo_url, output_base)
        results.append(result)
        if result["success"]:
            successful_scans += 1
    
    # Generate summary report
    summary_file = output_base / "batch_scan_summary.json"
    summary = {
        "scan_timestamp": datetime.now().isoformat(),
        "total_repositories": len(repo_urls),
        "successful_scans": successful_scans,
        "failed_scans": len(repo_urls) - successful_scans,
        "success_rate": successful_scans / len(repo_urls) if repo_urls else 0,
        "results": results
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n🎯 Batch Scan Complete!")
    print(f"📊 Summary saved to: {summary_file}")
    print(f"✅ Successful scans: {successful_scans}/{len(repo_urls)}")
    print(f"📁 Results directory: {output_base}")

if __name__ == "__main__":
    main()
