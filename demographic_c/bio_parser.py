"""Component C — Heuristic Bio-Text and Author Metadata Parser.

Extracts aggregate audience distributions (age bracket, professional interest,
regional geography, and primary language) from public author profiles and bios
sampled from linked discussion groups and post comments.

In accordance with the project specification:
    - Telegram broadcast channel subscriber lists are strictly private.
    - Demographic profiling operates exclusively on observable public data:
      Tier 2 audience engagement (authors of comments, replies, and forwards
      stored in ``raw_authors``).
    - All outputs are aggregate distributions (sums to 1.0), never individual
      census or surveillance labels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# Keyword taxonomies tailored to Indian defense, space, and tech policy audiences
AGE_BRACKET_KEYWORDS: dict[str, list[str]] = {
    "18-24": [
        "student", "undergrad", "undergraduate", "college", "aspirant", "learner",
        "fresher", "intern", "studying", "university", "candidate", "btech",
        "mtech", "bsc", "msc", "upsc aspirant", "iit", "nit", "gate aspirant",
    ],
    "25-34": [
        "engineer", "developer", "software", "designer", "researcher", "analyst",
        "founder", "co-founder", "professional", "specialist", "consultant",
        "architect", "scientist", "aerospace engineer", "vlsi", "data scientist",
        "working at", "tech enthusiast", "journalist", "reporter",
    ],
    "35-49": [
        "senior", "principal", "director", "manager", "head of", "lead",
        "veteran", "strategist", "expert", "faculty", "professor", "associate prof",
        "ex-officer", "editor", "advisor", "industry veteran", "commander",
    ],
    "50+": [
        "retired", "emeritus", "former director", "veteran officer", "ex-iaf",
        "ex-army", "ex-navy", "veteran diplomat", "former ambassador",
        "distinguished fellow", "senior adviser",
    ],
}

INTEREST_KEYWORDS: dict[str, list[str]] = {
    "Aerospace & Space": [
        "space", "isro", "satellite", "astronomy", "astrophysics", "rocket",
        "orbital", "gaganyaan", "chandrayaan", "in-space", "cosmos", "launch vehicle",
        "pslv", "gslv", "deep space", "planetary", "nasaspaceflight", "space policy",
    ],
    "Defense & Military": [
        "defense", "defence", "military", "drdo", "iaf", "army", "navy",
        "missile", "security", "indigenous", "atmanirbhar", "tejas", "amca",
        "su-30", "air force", "maritime", "corps", "infantry", "weapon", "warfare",
        "deterrence", "border security",
    ],
    "Geopolitics & Strategy": [
        "geopolitics", "policy", "strategy", "diplomacy", "international relations",
        "foreign affairs", "south asia", "indo-pacific", "national security", "bilateral",
        "multilateral", "unsc", "foreign policy", "diplomat", "strategic affairs",
    ],
    "Technology & Telecom": [
        "tech", "technology", "semiconductor", "vlsi", "software", "hardware",
        "cybersecurity", "telecom", "5g", "6g", "artificial intelligence", "ai",
        "computing", "quantum", "digital india", "fab", "microelectronics",
    ],
    "Academia & Research": [
        "research", "science", "scholar", "phd", "academic", "professor",
        "laboratory", "csir", "innovation", "physics", "stem", "education",
        "publications", "fellow",
    ],
}

GEOGRAPHY_KEYWORDS: dict[str, list[str]] = {
    "North India": [
        "delhi", "new delhi", "ncr", "noida", "gurgaon", "gurugram", "punjab",
        "chandigarh", "haryana", "jaipur", "rajasthan", "lucknow", "kanpur",
        "uttar pradesh", "up", "dehradun", "uttarakhand", "jammu", "kashmir",
        "shimla", "himachal",
    ],
    "South India": [
        "bengaluru", "bangalore", "chennai", "hyderabad", "karnataka", "kerala",
        "tamil nadu", "telangana", "andhra", "kochi", "trivandrum", "thiruvananthapuram",
        "mysore", "mysuru", "coimbatore", "visakhapatnam", "vizag",
    ],
    "West India": [
        "mumbai", "pune", "ahmedabad", "gujarat", "maharashtra", "surat",
        "nagpur", "goa", "vadodara", "dholera", "nashik",
    ],
    "East & Central India": [
        "kolkata", "calcutta", "odisha", "bhubaneswar", "west bengal", "bihar",
        "patna", "ranchi", "jharkhand", "assam", "guwahati", "northeast", "shillong",
        "bhopal", "indore", "madhya pradesh", "mp", "chhattisgarh", "raipur",
    ],
    "International / Diaspora": [
        "usa", "united states", "uk", "london", "canada", "europe", "germany",
        "singapore", "dubai", "uae", "australia", "diaspora", "overseas",
    ],
}

# Devanagari and Hinglish markers
DEVANAGARI_RANGE = re.compile(r"[\u0900-\u097F]")
HINGLISH_MARKERS = {
    "bhai", "kya", "shandar", "namaste", "hain", "desh", "bharat", "kamaal",
    "badhai", "shabaash", "ab", "mein", "hoga", "apna", "aur", "sab", "yeh",
    "bhi", "hum", "dil", "hindustan",
}


@dataclass
class AuthorProfileInput:
    """Input author profile record for demographic sampling."""

    author_id: str
    display_name: str | None = None
    bio_text: str | None = None
    sample_texts: list[str] = field(default_factory=list)


@dataclass
class DemographicInferenceResult:
    """Inferred aggregate distributions and confidence score."""

    total_authors_analyzed: int
    authors_with_bio_count: int
    age_bracket_dist: dict[str, float]
    interest_dist: dict[str, float]
    geography_dist: dict[str, float]
    language_dist: dict[str, float]
    inference_confidence: float


class BioParser:
    """Heuristic extractor parsing author bios and metadata into aggregate distributions."""

    def __init__(self) -> None:
        # Precompile lowercase regex patterns for efficiency
        self._age_patterns = {
            bracket: [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in kws]
            for bracket, kws in AGE_BRACKET_KEYWORDS.items()
        }
        self._interest_patterns = {
            interest: [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in kws]
            for interest, kws in INTEREST_KEYWORDS.items()
        }
        self._geography_patterns = {
            region: [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in kws]
            for region, kws in GEOGRAPHY_KEYWORDS.items()
        }

    def infer_author_attributes(
        self,
        bio: str | None,
        display_name: str | None = None,
        sample_texts: list[str] | None = None,
    ) -> dict[str, Any]:
        """Infer attributes for a single author.

        Args:
            bio: Author profile biography string.
            display_name: Author display handle or name.
            sample_texts: Sample messages or comments authored by this user.

        Returns:
            Dict containing matched age_brackets, interests, geographies, and languages.
        """
        combined_text = " ".join(
            filter(None, [display_name or "", bio or "", *(sample_texts or [])])
        ).strip()

        matched_ages: list[str] = []
        matched_interests: list[str] = []
        matched_geography: list[str] = []
        matched_language: str = "en"

        if not combined_text:
            return {
                "age_brackets": [],
                "interests": [],
                "geography": [],
                "language": "en",
                "has_signal": False,
            }

        # 1. Age bracket matching
        for bracket, patterns in self._age_patterns.items():
            if any(p.search(combined_text) for p in patterns):
                matched_ages.append(bracket)

        # 2. Interest matching
        for interest, patterns in self._interest_patterns.items():
            if any(p.search(combined_text) for p in patterns):
                matched_interests.append(interest)

        # 3. Geography matching
        for region, patterns in self._geography_patterns.items():
            if any(p.search(combined_text) for p in patterns):
                matched_geography.append(region)

        # 4. Language classification
        if DEVANAGARI_RANGE.search(combined_text):
            matched_language = "hi"
        else:
            tokens = set(re.findall(r"\b[a-zA-Z]+\b", combined_text.lower()))
            if tokens & HINGLISH_MARKERS:
                matched_language = "hi"  # Hinglish categorized under Indic/Hindi
            else:
                matched_language = "en"

        has_signal = bool(bio and bio.strip()) or bool(matched_ages or matched_interests or matched_geography)

        return {
            "age_brackets": matched_ages,
            "interests": matched_interests,
            "geography": matched_geography,
            "language": matched_language,
            "has_signal": has_signal,
        }

    def aggregate_profiles(
        self,
        profiles: list[AuthorProfileInput],
    ) -> DemographicInferenceResult:
        """Aggregate a cohort of author profiles into normalized distributions.

        Args:
            profiles: List of AuthorProfileInput objects.

        Returns:
            DemographicInferenceResult with probability distributions summing to 1.0.
        """
        total = len(profiles)
        if total == 0:
            return self._empty_result()

        age_counts = {k: 0.0 for k in AGE_BRACKET_KEYWORDS}
        interest_counts = {k: 0.0 for k in INTEREST_KEYWORDS}
        geo_counts = {k: 0.0 for k in GEOGRAPHY_KEYWORDS}
        geo_counts["Unspecified"] = 0.0
        lang_counts = {"en": 0.0, "hi": 0.0, "other": 0.0}

        authors_with_bio = 0
        signals_detected = 0

        for p in profiles:
            has_bio = bool(p.bio_text and p.bio_text.strip())
            if has_bio:
                authors_with_bio += 1

            inferred = self.infer_author_attributes(
                bio=p.bio_text,
                display_name=p.display_name,
                sample_texts=p.sample_texts,
            )

            if inferred["has_signal"]:
                signals_detected += 1

            # Accumulate age
            ages = inferred["age_brackets"]
            if ages:
                weight = 1.0 / len(ages)
                for a in ages:
                    age_counts[a] += weight
            else:
                # Prior distribution fallback for unclassified bios (25-34 dominant tech/policy demo)
                age_counts["18-24"] += 0.20
                age_counts["25-34"] += 0.45
                age_counts["35-49"] += 0.25
                age_counts["50+"] += 0.10

            # Accumulate interests
            interests = inferred["interests"]
            if interests:
                weight = 1.0 / len(interests)
                for it in interests:
                    interest_counts[it] += weight
            else:
                # Default baseline distribution for monitored domain
                interest_counts["Aerospace & Space"] += 0.35
                interest_counts["Defense & Military"] += 0.35
                interest_counts["Geopolitics & Strategy"] += 0.15
                interest_counts["Technology & Telecom"] += 0.10
                interest_counts["Academia & Research"] += 0.05

            # Accumulate geography
            geos = inferred["geography"]
            if geos:
                weight = 1.0 / len(geos)
                for g in geos:
                    geo_counts[g] += weight
            else:
                geo_counts["Unspecified"] += 1.0

            # Accumulate language
            lang = inferred["language"]
            if lang in lang_counts:
                lang_counts[lang] += 1.0
            else:
                lang_counts["other"] += 1.0

        # Normalize to probability distributions (sum to 1.0)
        age_dist = self._normalize_dict(age_counts, total)
        interest_dist = self._normalize_dict(interest_counts, total)
        geo_dist = self._normalize_dict(geo_counts, total)
        lang_dist = self._normalize_dict(lang_counts, total)

        # Confidence: weighted blend of bio availability (40%) and signal detection rate (60%)
        bio_ratio = authors_with_bio / total if total > 0 else 0.0
        signal_ratio = signals_detected / total if total > 0 else 0.0
        confidence = round(min(1.0, 0.4 * bio_ratio + 0.6 * signal_ratio + 0.15), 3)

        return DemographicInferenceResult(
            total_authors_analyzed=total,
            authors_with_bio_count=authors_with_bio,
            age_bracket_dist=age_dist,
            interest_dist=interest_dist,
            geography_dist=geo_dist,
            language_dist=lang_dist,
            inference_confidence=confidence,
        )

    @staticmethod
    def _normalize_dict(d: dict[str, float], total: float) -> dict[str, float]:
        """Normalize a dictionary of counts to proportions summing to 1.0."""
        s = sum(d.values())
        if s <= 0:
            n = len(d)
            return {k: round(1.0 / n, 4) for k in d}
        return {k: round(v / s, 4) for k, v in d.items()}

    @staticmethod
    def _empty_result() -> DemographicInferenceResult:
        """Return an empty default result when no authors are available."""
        return DemographicInferenceResult(
            total_authors_analyzed=0,
            authors_with_bio_count=0,
            age_bracket_dist={"18-24": 0.25, "25-34": 0.45, "35-49": 0.20, "50+": 0.10},
            interest_dist={
                "Aerospace & Space": 0.40,
                "Defense & Military": 0.35,
                "Geopolitics & Strategy": 0.15,
                "Technology & Telecom": 0.10,
            },
            geography_dist={"Unspecified": 1.0},
            language_dist={"en": 0.70, "hi": 0.30},
            inference_confidence=0.0,
        )
