"""Canonical country/nationality resolution from free-text names.

Handles the name spellings used by the transfermarkt dataset
(country_of_citizenship / country_of_birth) and maps them to the project's
canonical ISO-3166-1 alpha-2 codes (with England/Scotland/Wales/NI using the
reserved codes EN/SQ/WA/NI, and sport-specific codes where applicable).
"""

from __future__ import annotations

# canonical name -> code (superset covering common Transfermarkt spellings)
CANONICAL = {
    "Germany": "DE", "England": "EN", "Scotland": "SQ", "Wales": "WA",
    "Northern Ireland": "NI", "Spain": "ES", "Italy": "IT", "France": "FR",
    "Portugal": "PT", "Netherlands": "NL", "Belgium": "BE", "Switzerland": "CH",
    "Austria": "AT", "Denmark": "DK", "Sweden": "SE", "Norway": "NO",
    "Poland": "PL", "Czech Republic": "CZ", "Czechia": "CZ", "Slovakia": "SK",
    "Hungary": "HU", "Romania": "RO", "Bulgaria": "BG", "Greece": "GR",
    "Croatia": "HR", "Slovenia": "SI", "Serbia": "RS",
    "Serbia and Montenegro": "CS", "Yugoslavia": "YU", "Montenegro": "ME",
    "Bosnia and Herzegovina": "BA", "Bosnia-Herzegovina": "BA",
    "North Macedonia": "MK", "Albania": "AL", "Ukraine": "UA",
    "Russia": "RU", "Belarus": "BY", "Turkey": "TR", "Türkiye": "TR",
    "Republic of Ireland": "IE", "Ireland": "IE", "Iceland": "IS",
    "Finland": "FI", "Estonia": "EE", "Latvia": "LV", "Lithuania": "LT",
    "Georgia": "GE", "Armenia": "AM", "Azerbaijan": "AZ", "Kazakhstan": "KZ",
    "Israel": "IL", "Cyprus": "CY", "Malta": "MT", "Luxembourg": "LU",
    "Liechtenstein": "LI", "Andorra": "AD", "San Marino": "SM", "Monaco": "MC",
    "Faroe Islands": "FO", "Gibraltar": "GI",
    "Brazil": "BR", "Argentina": "AR", "Uruguay": "UY", "Chile": "CL",
    "Paraguay": "PY", "Peru": "PE", "Ecuador": "EC", "Colombia": "CO",
    "Venezuela": "VE", "Bolivia": "BO", "Mexico": "MX", "United States": "US",
    "Canada": "CA", "Costa Rica": "CR", "Panama": "PA", "Honduras": "HN",
    "El Salvador": "SV", "Guatemala": "GT", "Cuba": "CU", "Jamaica": "JM",
    "Trinidad and Tobago": "TT",
    "Japan": "JP", "South Korea": "KR", "Korea, South": "KR",
    "North Korea": "KP", "China": "CN", "Hong Kong": "HK", "Taiwan": "TW",
    "Australia": "AU", "New Zealand": "NZ", "India": "IN", "Iran": "IR",
    "Saudi Arabia": "SA", "Qatar": "QA", "United Arab Emirates": "AE",
    "South Africa": "ZA", "Nigeria": "NG", "Ghana": "GH", "Senegal": "SN",
    "Morocco": "MA", "Algeria": "DZ", "Tunisia": "TN", "Egypt": "EG",
    "Cameroon": "CM", "Ivory Coast": "CI", "Côte d'Ivoire": "CI",
    "Cote d'Ivoire": "CI", "DR Congo": "CD", "Congo": "CG",
    "Democratic Republic of the Congo": "CD", "Congo DR": "CD",
    "Cape Verde": "CV", "Cape Verde Islands": "CV", "Gambia": "GM",
    "Guinea": "GN", "Mali": "ML", "Burkina Faso": "BF", "Mali": "ML",
    "Gabon": "GA", "Angola": "AO", "Mozambique": "MZ", "Zambia": "ZM",
    "Zimbabwe": "ZW", "Kenya": "KE", "Tanzania": "TZ", "Uganda": "UG",
    "Ethiopia": "ET", "Somalia": "SO", "Sudan": "SD", "Libya": "LY",
    "Jordan": "JO", "Iraq": "IQ", "Syria": "SY", "Lebanon": "LB",
    "Palestine": "PS", "Oman": "OM", "Bahrain": "BH", "Kuwait": "KW",
    "Yemen": "YE", "Philippines": "PH", "Indonesia": "ID",
    "Thailand": "TH", "Vietnam": "VN", "Malaysia": "MY", "Singapore": "SG",
    "Bangladesh": "BD", "Pakistan": "PK", "Sri Lanka": "LK",
    "Afghanistan": "AF", "Uzbekistan": "UZ", "Kyrgyzstan": "KG",
    "Tajikistan": "TJ", "Turkmenistan": "TM", "Moldova": "MD",
    "Curacao": "CW", "Curaçao": "CW", "Aruba": "AW", "Suriname": "SR",
    "Guyana": "GY", "Haiti": "HT", "Dominican Republic": "DO",
    "Puerto Rico": "PR", "New Caledonia": "NC", "Tahiti": "PF",
    "French Guiana": "GF", "Martinique": "MQ", "Guadeloupe": "GP",
    "Saint Kitts and Nevis": "KN", "Saint Lucia": "LC",
    "Saint Vincent and the Grenadines": "VC", "Grenada": "GD",
    "Barbados": "BB", "Bahamas": "BS", "Bermuda": "BM", "Cayman Islands": "KY",
    "Nicaragua": "NIC",  # project code (NIC) to avoid clash with Northern Ireland (NI)
}

# Football-specific nationality codes where ISO differs / country not ISO.
SPORT_CODES = {"EN": "England", "SQ": "Scotland", "WA": "Wales", "NI": "Northern Ireland"}


def canonical_country_code(name: str | None) -> str:
    """Map a Transfermarkt-style citizenship/birth country name to a canonical code.

    Returns "" when unknown (callers should treat as unavailable, not guess).
    """
    if not name or pd_isna(name):
        return ""
    n = str(name).strip()
    if n in CANONICAL:
        return CANONICAL[n]
    return ""


def pd_isna(x) -> bool:
    import pandas as pd
    return pd.isna(x)