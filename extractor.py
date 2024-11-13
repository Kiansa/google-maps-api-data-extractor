import os
from dotenv import load_dotenv
import requests
import json
import time
import re

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("PLACES_API_KEY")
CATEGORY = os.getenv("CATEGORY")
CITIES = os.getenv("CITIES").split(",")  # Split comma-separated cities into a list

# Email regex and contact regex patterns
email_regex = r'(([\w\.\-]+)@([\w\-]+)((\.(\w){2,3})+))'
contact_regex = r'(href=[\'"]?contact([^\'" >]+)")'
ignore_ext = [".jpg", ".jpeg", ".png", ".gif", ".webp"]

# Check if API_KEY, CATEGORY, and CITIES are loaded
if not API_KEY:
    print("Error: PLACES_API_KEY is missing or could not be loaded from the .env file.")
else:
    print("API Key loaded successfully.")

if not CATEGORY:
    print("Error: CATEGORY is missing or could not be loaded from the .env file.")
else:
    print(f"Search category loaded: {CATEGORY}")

if not CITIES:
    print("Error: CITIES are missing or could not be loaded from the .env file.")
else:
    print(f"Cities loaded: {CITIES}")

def get_companies(city, api_key, category):
    # Initialize pagination variables
    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    all_companies = []
    page = 0
    next_page_token = None

    # Loop through pages
    while page < 20:
        # Set up query parameters, including the next page token if available
        search_params = {
            "query": f"{category} in {city}",
            "key": api_key
        }
        if next_page_token:
            search_params["pagetoken"] = next_page_token

        # Perform request
        response = requests.get(search_url, params=search_params)
        data = response.json()
        
        # Append current page results
        results = data.get("results", [])
        for result in results:
            place_id = result["place_id"]
            details = get_place_details(place_id, api_key, city)
            if details:
                all_companies.append(details)

        # Check for next page token and increment page count
        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break  # No more pages
        page += 1

        # Google may require a short delay before using next_page_token
        time.sleep(2)

    return all_companies

def get_place_details(place_id, api_key, city):
    # Get details for a specific place ID with regionCode to ensure international phone format
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    details_params = {
        "place_id": place_id,
        "fields": "name,website,international_phone_number,formatted_address",
        "key": api_key
    }

    response = requests.get(details_url, params=details_params)
    result = response.json().get("result", {})

    # Extract relevant fields, including email using the find_email function
    website = result.get("website", "")
    email = find_email(website) if website else ""

    return {
        "name": result.get("name", ""),
        "website": website,
        "phone": result.get("international_phone_number", ""),
        "email": email,
        "address": result.get("formatted_address", ""),
        "city": city,
        "postcode": get_postcode(result.get("formatted_address", ""))
    }

def find_email(website):
    """Tries to find an email address on the given website."""
    return find_regex_html(website, email_regex, ignore_ext) or ""

def find_regex_html(url, regex, false_hit_chars=[]):
    """Fetches a URL and applies a regex to find email addresses."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        rsp = requests.get(url, headers=headers, timeout=10)
        if rsp.status_code == 200:
            matches = re.findall(regex, rsp.text)
            if matches:
                for match in matches:
                    if not any(ext in match[0] for ext in false_hit_chars):
                        return match[0]
    except:
        print(f"Error fetching or processing {url}")
    return None

def get_postcode(address):
    # Extract postal code from address if available
    if address:
        # Use regex to capture the postal code (assuming it's typically numeric)
        match = re.search(r"\b\d{4,5}\b", address)
        if match:
            return match.group(0)
    return ""

def save_to_json(data, filename):
    with open(filename, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Call functions for each city
for city in CITIES:
    city = city.strip()  # Remove any extra whitespace around city names
    companies = get_companies(city, API_KEY, CATEGORY)
    filename = f"{CATEGORY}-{city}.json".replace(" ", "_").lower()
    save_to_json(companies, filename)
    print(f"Data saved to {filename}")
