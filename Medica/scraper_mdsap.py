#!/usr/bin/env python3
"""
MEDICA Scraper for MDSAP-certified Chinese companies
Scrapes 11 companies from: https://www.medica-tradefair.com/vis/v1/en/search?_query=mdsap&f_country=CN
"""

import json
import os
import time
import re
import requests
from playwright.sync_api import sync_playwright
from datetime import datetime

def sanitize_filename(name):
    """Remove invalid characters from filenames"""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def download_file(url, folder, filename):
    """Download a file from URL to the specified folder"""
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            path = os.path.join(folder, filename)
            with open(path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"    Error downloading {url}: {e}")
    return False

def close_modal(page):
    """Try to close the modal overlay"""
    try:
        # The close button has this structure: <button><div class="icon-button__inner"><svg class="svg-icon--close">...
        close_selectors = [
            "button:has(.svg-icon--close)",  # Button containing the close SVG icon
            "button:has-text('Close')",
            ".overlay button[type='button']",
            "button[aria-label='Close']"
        ]

        for selector in close_selectors:
            close_btn = page.query_selector(selector)
            if close_btn:
                close_btn.click()
                page.wait_for_timeout(1000)
                return True

        # If no close button found, try pressing Escape
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)
        return True
    except Exception as e:
        print(f"    Warning: Could not close modal: {e}")
        return False

def exhibitor_already_scraped(exhibitor_name, base_dir="downloads_mdsap"):
    """Check if exhibitor was already downloaded"""
    safe_name = sanitize_filename(exhibitor_name)
    exhibitor_dir = os.path.join(base_dir, safe_name)
    info_file = os.path.join(exhibitor_dir, "info.json")
    return os.path.exists(info_file)

def scrape_modal_data(page, exhibitor_name, exhibitor_dir):
    """Extract all data from the exhibitor modal"""
    exhibitor_data = {
        "name": exhibitor_name,
        "location": "",
        "company_description": "",
        "email": None,
        "phone": None,
        "website": None,
        "address": None,
        "raw_text": "",
        "product_images": [],  # List of local filenames
        "documents": [],       # List of local filenames
        "event": "MEDICA 2025",
        "has_mdsap": True,     # Flag to indicate MDSAP certification
        "scraped_at": None
    }

    try:
        # Wait for modal to appear
        page.wait_for_selector("div.overlay", timeout=10000)
        page.wait_for_timeout(2000)  # Let content load

        # Extract company description
        try:
            desc_container = page.query_selector(".overlay .company-description, .overlay p")
            if desc_container:
                exhibitor_data["company_description"] = desc_container.inner_text().strip()
        except:
            pass

        # Extract company data (address, email, phone, website)
        try:
            company_data_text = page.evaluate("""() => {
                const section = document.querySelector('.overlay [class*="company-data"], .overlay [class*="Company data"]');
                return section ? section.innerText : '';
            }""")

            if company_data_text:
                # Parse email
                email_match = re.search(r'E-mail:\s*(.+)', company_data_text)
                if email_match:
                    exhibitor_data["email"] = email_match.group(1).strip()

                # Parse phone
                phone_match = re.search(r'Phone:\s*(.+)', company_data_text)
                if phone_match:
                    exhibitor_data["phone"] = phone_match.group(1).strip()

                # Parse website
                web_match = re.search(r'Web:\s*(.+)', company_data_text)
                if web_match:
                    exhibitor_data["website"] = web_match.group(1).strip()

                # Parse address (lines before email)
                lines = company_data_text.split('\n')
                address_lines = []
                for line in lines:
                    if any(x in line for x in ['E-mail:', 'Phone:', 'Web:']):
                        break
                    if line.strip():
                        address_lines.append(line.strip())
                if address_lines:
                    exhibitor_data["address"] = ' '.join(address_lines)
        except Exception as e:
            print(f"    Error extracting company data: {e}")

        # Get all text from modal
        try:
            modal_text = page.evaluate("""() => {
                const modal = document.querySelector('.overlay');
                return modal ? modal.innerText : '';
            }""")
            exhibitor_data["raw_text"] = modal_text
        except:
            pass

        # Check for PDF downloads
        try:
            pdf_links = page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('.overlay a[href$=".pdf"]'));
                return links.map(a => ({href: a.href, text: a.innerText}));
            }""")

            for pdf in pdf_links:
                pdf_url = pdf['href']
                pdf_name = sanitize_filename(pdf['text']) + ".pdf"
                if not pdf_name.endswith(".pdf"):
                    pdf_name += ".pdf"

                print(f"    Found PDF: {pdf_name}")
                if download_file(pdf_url, exhibitor_dir, pdf_name):
                    exhibitor_data["documents"].append(pdf_name)
        except Exception as e:
            print(f"    Error checking PDFs: {e}")

        # Try to click "Go to Exhibitor Profile" button - this opens a NEW TAB
        try:
            # Try multiple selectors for the button
            full_profile_btn = page.query_selector("text=Go to Exhibitor Profile")
            if not full_profile_btn:
                full_profile_btn = page.query_selector("a[title='Go to Exhibitor Profile']")
            if not full_profile_btn:
                full_profile_btn = page.query_selector(".overlay a:has-text('Go to Exhibitor Profile')")

            if full_profile_btn:
                print("    Clicking 'Go to Exhibitor Profile' (opens new tab)...")

                # Wait for new page/tab to open
                with page.context.expect_page() as new_page_info:
                    full_profile_btn.click(force=True)

                new_page = new_page_info.value
                new_page.wait_for_load_state("domcontentloaded")
                new_page.wait_for_timeout(3000)

                # Check if we're on the full profile page
                current_url = new_page.url
                on_full_page = "exhprofiles" in current_url

                if on_full_page:
                    print("    Successfully opened full profile page in new tab")

                    # Scrape the Profile tab data (includes products section at the bottom)
                    try:
                        # Get full page text
                        profile_text = new_page.evaluate("""() => {
                            return document.body.innerText;
                        }""")
                        exhibitor_data["raw_text"] = profile_text

                        # Extract company description
                        company_info = new_page.query_selector(".profile-info, article")
                        if company_info:
                            company_text = company_info.inner_text()
                            exhibitor_data["company_description"] = company_text[:500]

                        # Scroll down to load all content including products section
                        print("    Scrolling down to load products...")
                        new_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        new_page.wait_for_timeout(2000)

                        # Scrape ALL images from the page (Profile tab has products at the bottom)
                        print("    Scraping images from profile page...")
                        images = new_page.evaluate("""() => {
                            const imgs = Array.from(document.querySelectorAll('article img'));
                            return imgs.map(img => img.src);
                        }""")

                        unique_images = [img for img in list(set(images)) if img.startswith('http')]
                        print(f"    Found {len(unique_images)} product images")

                        for idx, img_url in enumerate(unique_images):
                            img_ext = ".png"
                            if ".jpg" in img_url or ".jpeg" in img_url:
                                img_ext = ".jpg"

                            img_filename = f"product_{idx+1}{img_ext}"
                            print(f"    Downloading: {img_filename}")

                            if download_file(img_url, exhibitor_dir, img_filename):
                                exhibitor_data["product_images"].append(img_filename)

                    except Exception as e:
                        print(f"    Error scraping profile page: {e}")

                    # Close the new tab - this returns us to the search page
                    print("    Closing exhibitor profile tab...")
                    new_page.close()
                    page.wait_for_timeout(1000)

                    # Now we're back on search page, but modal is still open - close it
                    print("    Back on search page, closing modal...")
                    # The close button is in the top right - it's an X button
                    close_btn = page.query_selector(".overlay button:has(.svg-icon--close)")
                    if close_btn:
                        close_btn.click()
                        page.wait_for_timeout(1000)
                    else:
                        # Fallback to Escape key
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(1000)
                else:
                    print("    Could not reach full profile page")
                    new_page.close()
                    page.wait_for_timeout(1000)
                    # Still need to close modal
                    close_btn = page.query_selector(".overlay button:has(.svg-icon--close)")
                    if close_btn:
                        close_btn.click()
                        page.wait_for_timeout(1000)
            else:
                print("    'Go to Exhibitor Profile' button not found")
        except Exception as e:
            print(f"    Error accessing full profile: {e}")

    except Exception as e:
        print(f"    Error scraping modal: {e}")

    return exhibitor_data

def run():
    base_download_dir = "downloads_mdsap"
    if not os.path.exists(base_download_dir):
        os.makedirs(base_download_dir)

    all_exhibitors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Start with the MDSAP search URL directly (already has China filter applied)
        url = "https://www.medica-tradefair.com/vis/v1/en/search?_query=mdsap&f_country=CN"
        print(f"\n{'='*70}")
        print(f"MEDICA MDSAP SCRAPER - Chinese Companies")
        print(f"{'='*70}")
        print(f"\nNavigating to {url}\n")

        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"Navigation error: {e}")
            browser.close()
            return

        # Wait for page to load fully
        page.wait_for_timeout(5000)

        # Wait for results to load
        try:
            page.wait_for_selector("article", timeout=60000)
            print("✅ Page loaded successfully\n")
        except Exception as e:
            print(f"❌ Error waiting for results: {e}")
            browser.close()
            return

        # Get count of results
        try:
            result_count_text = page.evaluate("""() => {
                const counter = document.querySelector('.search-filter-results-counter');
                return counter ? counter.innerText : '0';
            }""")
            print(f"📊 Found: {result_count_text}\n")
        except:
            pass

        total_skipped = 0
        total_scraped = 0

        print(f"{'='*70}")
        print(f"SCRAPING EXHIBITORS")
        print(f"{'='*70}\n")

        # Get all result items on this page
        items = page.query_selector_all("article")
        print(f"Found {len(items)} exhibitor cards on page.\n")

        for item_idx, item in enumerate(items):
            try:
                # Extract name from the card
                name_el = item.query_selector(".teaser-tile__title span")
                name = name_el.inner_text().strip() if name_el else "Unknown"

                # Extract location
                location_el = item.query_selector(".teaser-tile__location")
                location = location_el.inner_text().strip() if location_el else "N/A"

                print(f"[{item_idx+1}/{len(items)}] {name}")
                print(f"  Location: {location}")

                # Check if already scraped
                if exhibitor_already_scraped(name, base_download_dir):
                    print(f"  ⏭️  SKIPPED - Already downloaded\n")
                    total_skipped += 1
                    continue

                # Create directory for this exhibitor
                safe_name = sanitize_filename(name)
                exhibitor_dir = os.path.join(base_download_dir, safe_name)
                if not os.path.exists(exhibitor_dir):
                    os.makedirs(exhibitor_dir)

                # Click the card to open modal
                print("  Opening exhibitor details...")
                item.click()
                page.wait_for_timeout(2000)

                # Scrape data from modal
                exhibitor_data = scrape_modal_data(page, name, exhibitor_dir)
                exhibitor_data["location"] = location

                # Add timestamp
                exhibitor_data["scraped_at"] = datetime.now().isoformat()

                # Save to JSON (individual file)
                with open(os.path.join(exhibitor_dir, "info.json"), "w", encoding="utf-8") as f:
                    json.dump(exhibitor_data, f, indent=2, ensure_ascii=False)

                # Add to collection with relative paths for images
                exhibitor_summary = {
                    **exhibitor_data,
                    "exhibitor_dir": exhibitor_dir,
                    "product_image_paths": [os.path.join(exhibitor_dir, img) for img in exhibitor_data["product_images"]],
                    "document_paths": [os.path.join(exhibitor_dir, doc) for doc in exhibitor_data["documents"]]
                }
                all_exhibitors.append(exhibitor_summary)
                total_scraped += 1

                # Modal should already be closed by scrape_modal_data function
                # If not, try to close it
                if page.query_selector(".overlay"):
                    print("  Modal still open, closing it...")
                    close_modal(page)
                    page.wait_for_timeout(1000)

                print(f"  ✅ Completed\n")

            except Exception as e:
                print(f"  ❌ Error processing item: {e}\n")
                # Try to close modal anyway
                try:
                    close_modal(page)
                except:
                    pass

        browser.close()

    # Save summary JSON (database-ready format)
    if all_exhibitors:
        output_json = "exhibitors_mdsap.json"
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(all_exhibitors, f, indent=2, ensure_ascii=False)

        # Create CSV for easy database import
        import csv
        csv_file = "exhibitors_mdsap.csv"
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            # Define fields matching database schema
            fieldnames = ["name", "location", "company_description", "email", "phone",
                         "website", "address", "raw_text", "event", "has_mdsap", "scraped_at",
                         "exhibitor_dir", "num_images", "num_documents"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for exhibitor in all_exhibitors:
                writer.writerow({
                    "name": exhibitor["name"],
                    "location": exhibitor["location"],
                    "company_description": exhibitor["company_description"][:500] if exhibitor["company_description"] else "",
                    "email": exhibitor.get("email") or "",
                    "phone": exhibitor.get("phone") or "",
                    "website": exhibitor.get("website") or "",
                    "address": exhibitor.get("address") or "",
                    "raw_text": exhibitor["raw_text"],
                    "event": exhibitor["event"],
                    "has_mdsap": exhibitor.get("has_mdsap", True),
                    "scraped_at": exhibitor["scraped_at"],
                    "exhibitor_dir": exhibitor["exhibitor_dir"],
                    "num_images": len(exhibitor["product_images"]),
                    "num_documents": len(exhibitor["documents"])
                })

    print(f"\n{'='*70}")
    print(f"SCRAPING COMPLETE!")
    print(f"{'='*70}")
    print(f"✅ Total NEW exhibitors scraped: {total_scraped}")
    print(f"⏭️  Total SKIPPED (already downloaded): {total_skipped}")
    print(f"📂 Data saved to: {base_download_dir}/")
    if all_exhibitors:
        print(f"📄 Summary JSON: {output_json}")
        print(f"📊 Summary CSV: {csv_file}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    run()
