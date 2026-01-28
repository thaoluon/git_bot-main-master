import os
import httpx
from dotenv import load_dotenv
import re

load_dotenv()

# Provider selection: "opencage", "google", "nominatim", "claude", "gemini", "groq"
LOCATION_PROVIDER = os.getenv("LOCATION_PROVIDER", "nominatim").lower()

# API Keys
OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Iran province/territory names and common Iran location keywords
US_STATES = {
    'alborz',
    'ardabil',
    'bushehr',
    'chaharmahal and bakhtiari', 'chahar mahal and bakhtiari',
    'east azerbaijan', 'east azarbaijan',
    'fars',
    'gilan',
    'golestan',
    'hamadan', 'hamedan',
    'hormozgan',
    'ilam',
    'isfahan', 'esfahan',
    'kerman',
    'kermanshah',
    'khuzestan',
    'kohgiluyeh and boyer-ahmad', 'kohgiluyeh and boyer ahmad',
    'kurdistan',
    'lorestan', 'lurestan',
    'markazi',
    'mazandaran',
    'north khorasan', 'northern khorasan',
    'qazvin',
    'qom',
    'razavi khorasan', 'khorasan razavi',
    'semnan',
    'sistan and baluchestan', 'sistan and baluchistan',
    'south khorasan', 'southern khorasan',
    'tehran',
    'west azerbaijan', 'west azarbaijan',
    'yazd',
    'zanjan',
}

US_STATE_CODES = {
    'alb',  # alborz
    'ard',  # ardabil
    'bsh',  # bushehr
    'cnb', 'chb',  # chaharmahal and bakhtiari
    'eaz',  # east azerbaijan
    'far',  # fars
    'gil',  # gilan
    'gol',  # golestan
    'ham',  # hamadan
    'hor',  # hormozgan
    'ila',  # ilam
    'isf', 'esf',  # isfahan
    'ker',  # kerman
    'krm',  # kermanshah
    'khu',  # khuzestan
    'kba',  # kohgiluyeh and boyer-ahmad
    'kur',  # kurdistan
    'lor',  # lorestan
    'mar',  # markazi
    'maz',  # mazandaran
    'nkh',  # north khorasan
    'qaz',  # qazvin
    'qom',  # qom
    'rkh',  # razavi khorasan
    'sem',  # semnan
    'sba',  # sistan and baluchestan
    'skh',  # south khorasan
    'teh',  # tehran
    'waz',  # west azerbaijan
    'yaz',  # yazd
    'zan',  # zanjan
}

US_KEYWORDS = {
    'iran',
    'ir', 'i.r.', 'i.r',               # common abbreviation for "Islamic Republic"
    'islamic republic of iran',
    'persia', 'persian',
    'tehran',
    'iranian',
}


async def is_us_location_geocoding(location_str: str) -> bool:
    """Check if location is in Iran using geocoding APIs"""
    if not location_str:
        return False
    
    location_lower = location_str.lower()
    
    # Quick keyword check first
    if any(keyword in location_lower for keyword in US_KEYWORDS):
        return True
    
    # Check for Iran province/territory names or codes
    words = re.findall(r'\b\w+\b', location_lower)
    if any(word in US_STATES or word in US_STATE_CODES for word in words):
        return True
    
    # Use geocoding API
    if LOCATION_PROVIDER == "opencage":
        return await _check_with_opencage(location_str)
    elif LOCATION_PROVIDER == "google":
        return await _check_with_google(location_str)
    elif LOCATION_PROVIDER == "nominatim":
        return await _check_with_nominatim(location_str)
    
    return False


async def _check_with_nominatim(location_str: str) -> bool:
    """Check location using Nominatim (OpenStreetMap) - FREE"""
    try:
        async with httpx.AsyncClient() as client:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": location_str,
                "format": "json",
                "addressdetails": 1,
                "limit": 1
            }
            headers = {
                "User-Agent": "GitHub-User-Bot/1.0"  # Required by Nominatim
            }
            
            res = await client.get(url, params=params, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data and len(data) > 0:
                    address = data[0].get("address", {})
                    country_code = address.get("country_code", "").lower()
                    return country_code == ""
    except Exception as e:
        print(f"[Nominatim Error] {e}")
    return False


async def _check_with_opencage(location_str: str) -> bool:
    """Check location using OpenCage Geocoding API"""
    if not OPENCAGE_API_KEY:
        print("[ERROR] OPENCAGE_API_KEY not set")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.opencagedata.com/geocode/v1/json"
            params = {
                "q": location_str,
                "key": OPENCAGE_API_KEY,
                "limit": 1
            }
            
            res = await client.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("results"):
                    country_code = data["results"][0].get("components", {}).get("country_code", "").lower()
                    return country_code == ""
    except Exception as e:
        print(f"[OpenCage Error] {e}")
    return False


async def _check_with_google(location_str: str) -> bool:
    """Check location using Google Maps Geocoding API"""
    if not GOOGLE_MAPS_API_KEY:
        print("[ERROR] GOOGLE_MAPS_API_KEY not set")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": location_str,
                "key": GOOGLE_MAPS_API_KEY
            }
            
            res = await client.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("results"):
                    address_components = data["results"][0].get("address_components", [])
                    for component in address_components:
                        if "country" in component.get("types", []):
                            country_code = component.get("short_name", "").lower()
                            return country_code == ""
    except Exception as e:
        print(f"[Google Maps Error] {e}")
    return False


async def is_us_location_llm(location_str: str) -> bool:
    """Check if location is in Iran using LLM providers"""
    if not location_str:
        return False
    
    prompt = (
        f"Given the user's location: '{location_str}', determine whether they are located in Iran. "
        "Respond only with 'Yes' or 'No'."
    )
    
    if LOCATION_PROVIDER == "claude":
        return await _check_with_claude(prompt)
    elif LOCATION_PROVIDER == "gemini":
        return await _check_with_gemini(prompt)
    elif LOCATION_PROVIDER == "groq":
        return await _check_with_groq(prompt)
    
    return False


async def _check_with_claude(prompt: str) -> bool:
    """Check location using Anthropic Claude API"""
    if not ANTHROPIC_API_KEY:
        print("[ERROR] ANTHROPIC_API_KEY not set")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            body = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            res = await client.post(url, headers=headers, json=body, timeout=30)
            if res.status_code == 200:
                data = res.json()
                answer = data.get("content", [{}])[0].get("text", "").strip().lower()
                return answer.startswith("yes")
    except Exception as e:
        print(f"[Claude Error] {e}")
    return False


async def _check_with_gemini(prompt: str) -> bool:
    """Check location using Google Gemini API"""
    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY not set")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
            body = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            res = await client.post(url, json=body, timeout=30)
            if res.status_code == 200:
                data = res.json()
                answer = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip().lower()
                return answer.startswith("yes")
    except Exception as e:
        print(f"[Gemini Error] {e}")
    return False


async def _check_with_groq(prompt: str) -> bool:
    """Check location using Groq API"""
    if not GROQ_API_KEY:
        print("[ERROR] GROQ_API_KEY not set")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            body = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 10
            }
            
            res = await client.post(url, headers=headers, json=body, timeout=30)
            if res.status_code == 200:
                data = res.json()
                answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
                return answer.startswith("yes")
    except Exception as e:
        print(f"[Groq Error] {e}")
    return False


async def is_us_location(location_str: str, retries=2) -> bool:
    """
    Main function to check if location is in Iran.
    Supports multiple providers configured via LOCATION_PROVIDER env var.
    
    Providers:
    - "nominatim" (default, FREE) - OpenStreetMap Nominatim
    - "opencage" - OpenCage Geocoding API
    - "google" - Google Maps Geocoding API
    - "claude" - Anthropic Claude API
    - "gemini" - Google Gemini API
    - "groq" - Groq API
    """
    if not location_str:
        return False
    
    # Use geocoding APIs (recommended)
    if LOCATION_PROVIDER in ["nominatim", "opencage", "google"]:
        for _ in range(retries):
            result = await is_us_location_geocoding(location_str)
            if result:
                return True
        return False
    
    # Use LLM providers
    elif LOCATION_PROVIDER in ["claude", "gemini", "groq"]:
        for _ in range(retries):
            result = await is_us_location_llm(location_str)
            if result:
                return True
        return False
    
    else:
        print(f"[ERROR] Unknown LOCATION_PROVIDER: {LOCATION_PROVIDER}")
        print(f"[INFO] Using default: nominatim")
        # Fallback to nominatim
        return await _check_with_nominatim(location_str)


async def get_country_code(location_str: str, retries=2) -> str:
    """
    Get country code (ISO 2-letter code) from location string.
    Returns uppercase country code (e.g., 'PK', 'US', 'NO') or None if not found.
    Supports multiple providers configured via LOCATION_PROVIDER env var.
    """
    if not location_str:
        return None
    
    location_lower = location_str.lower()
    
    # Quick keyword check for Iran
    if any(keyword in location_lower for keyword in US_KEYWORDS):
        return ""
    
    # Check for Iran province/territory names or codes
    words = re.findall(r'\b\w+\b', location_lower)
    if any(word in US_STATES or word in US_STATE_CODES for word in words):
        return ""
    
    # Use geocoding APIs (recommended)
    if LOCATION_PROVIDER in ["nominatim", "opencage", "google"]:
        for _ in range(retries):
            country_code = await _get_country_code_geocoding(location_str)
            if country_code:
                return country_code.upper()
        return None
    
    # Use LLM providers (fallback - less reliable for country codes)
    elif LOCATION_PROVIDER in ["claude", "gemini", "groq"]:
        # For LLM, we'll use geocoding as fallback
        for _ in range(retries):
            country_code = await _get_country_code_geocoding(location_str)
            if country_code:
                return country_code.upper()
        return None
    
    else:
        print(f"[ERROR] Unknown LOCATION_PROVIDER: {LOCATION_PROVIDER}")
        print(f"[INFO] Using default: nominatim")
        # Fallback to nominatim
        country_code = await _get_country_code_nominatim(location_str)
        return country_code.upper() if country_code else None


async def _get_country_code_geocoding(location_str: str) -> str:
    """Get country code using geocoding APIs"""
    if LOCATION_PROVIDER == "opencage":
        return await _get_country_code_opencage(location_str)
    elif LOCATION_PROVIDER == "google":
        return await _get_country_code_google(location_str)
    elif LOCATION_PROVIDER == "nominatim":
        return await _get_country_code_nominatim(location_str)
    return None


async def _get_country_code_nominatim(location_str: str) -> str:
    """Get country code using Nominatim (OpenStreetMap) - FREE"""
    try:
        async with httpx.AsyncClient() as client:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": location_str,
                "format": "json",
                "addressdetails": 1,
                "limit": 1
            }
            headers = {
                "User-Agent": "GitHub-User-Bot/1.0"  # Required by Nominatim
            }
            
            res = await client.get(url, params=params, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data and len(data) > 0:
                    address = data[0].get("address", {})
                    country_code = address.get("country_code", "")
                    return country_code if country_code else None
    except Exception as e:
        print(f"[Nominatim Error] {e}")
    return None


async def _get_country_code_opencage(location_str: str) -> str:
    """Get country code using OpenCage Geocoding API"""
    if not OPENCAGE_API_KEY:
        print("[ERROR] OPENCAGE_API_KEY not set")
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.opencagedata.com/geocode/v1/json"
            params = {
                "q": location_str,
                "key": OPENCAGE_API_KEY,
                "limit": 1
            }
            
            res = await client.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("results"):
                    country_code = data["results"][0].get("components", {}).get("country_code", "")
                    return country_code if country_code else None
    except Exception as e:
        print(f"[OpenCage Error] {e}")
    return None


async def _get_country_code_google(location_str: str) -> str:
    """Get country code using Google Maps Geocoding API"""
    if not GOOGLE_MAPS_API_KEY:
        print("[ERROR] GOOGLE_MAPS_API_KEY not set")
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": location_str,
                "key": GOOGLE_MAPS_API_KEY
            }
            
            res = await client.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("results"):
                    address_components = data["results"][0].get("address_components", [])
                    for component in address_components:
                        if "country" in component.get("types", []):
                            country_code = component.get("short_name", "")
                            return country_code if country_code else None
    except Exception as e:
        print(f"[Google Maps Error] {e}")
    return None
