"""
Time-Zone & Working Hours Feasibility Engine
Evaluates time-zone math, circadian impact, and overlap feasibility between
cross-border employers and global candidates.
"""

import re
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
from zoneinfo import ZoneInfo
from enum import Enum

class FlexibilityTier(str, Enum):
    STRICT_DAYLIGHT = "STRICT_DAYLIGHT"   # 08:00 - 20:00 only
    MODERATE_EVENING = "MODERATE_EVENING" # Up to 00:00 (midnight)
    NIGHT_OWL = "NIGHT_OWL"               # Open to graveyard/night (22:00 - 07:00)

class FeasibilityStatus(str, Enum):
    OPTIMAL = "OPTIMAL"           # 08:00 - 19:00 local, zero circadian disruption
    MANAGEABLE = "MANAGEABLE"     # 19:00 - 23:30 local, moderate evening shift
    EXTREME = "EXTREME"           # 23:30 - 06:00 local, night shift
    INCOMPATIBLE = "INCOMPATIBLE" # Math impossibility or strict preference conflict

# Known abbreviations mapped to representative IANA timezone regions
ABBREVIATION_TO_IANA = {
    # US & Canada
    "PT": "America/Los_Angeles",
    "PST": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "ET": "America/New_York",
    "EST": "America/New_York",
    "EDT": "America/New_York",
    "CT": "America/Chicago",
    "CST": "America/Chicago",
    "CDT": "America/Chicago",
    "MT": "America/Denver",
    "MST": "America/Denver",
    "MDT": "America/Denver",
    "AKST": "America/Anchorage",
    "AKDT": "America/Anchorage",
    "HST": "Pacific/Honolulu",
    "US BUSINESS HOURS": "America/New_York",
    "US HOURS": "America/New_York",

    # UK & Europe
    "GMT": "Europe/London",
    "BST": "Europe/London", # UK British Summer Time (when in UK context)
    "WET": "Europe/Lisbon",
    "WEST": "Europe/Lisbon",
    "CET": "Europe/Berlin",
    "CEST": "Europe/Berlin",
    "EET": "Europe/Athens",
    "EEST": "Europe/Athens",
    "EU BUSINESS HOURS": "Europe/Berlin",
    "UK BUSINESS HOURS": "Europe/London",

    # APAC & Middle East
    "IST": "Asia/Kolkata",
    "SGT": "Asia/Singapore",
    "HKT": "Asia/Hong_Kong",
    "JST": "Asia/Tokyo",
    "KST": "Asia/Seoul",
    "AEST": "Australia/Sydney",
    "AEDT": "Australia/Sydney",
    "ACST": "Australia/Adelaide",
    "ACDT": "Australia/Adelaide",
    "AWST": "Australia/Perth",
    "NZST": "Pacific/Auckland",
    "NZDT": "Pacific/Auckland",
    "GST": "Asia/Dubai",
    "AST": "Asia/Riyadh",
    "APAC BUSINESS HOURS": "Asia/Singapore",
    
    # Bangladesh
    "BDST": "Asia/Dhaka",
    "DHAKA": "Asia/Dhaka",
    "BANGLADESH": "Asia/Dhaka"
}

def parse_time_str(t_str: str) -> float:
    """Parse '09:00', '9:30', '9am', '5pm' into decimal hours (e.g., 9.5)."""
    t_clean = t_str.strip().lower()
    
    # Check 12-hour am/pm
    m_12 = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$', t_clean)
    if m_12:
        hours = int(m_12.group(1))
        mins = int(m_12.group(2) or 0)
        meridiem = m_12.group(3)
        if meridiem == 'pm' and hours != 12:
            hours += 12
        elif meridiem == 'am' and hours == 12:
            hours = 0
        return hours + (mins / 60.0)

    # Check 24-hour hh:mm
    m_24 = re.match(r'^(\d{1,2})(?::(\d{2}))?$', t_clean)
    if m_24:
        hours = int(m_24.group(1))
        mins = int(m_24.group(2) or 0)
        return hours + (mins / 60.0)

    return 9.0

def format_decimal_hour(h: float, include_offset: int = 0) -> str:
    """Format decimal hour into 'HH:MM' with optional (+1) day indicator."""
    day_shift = int(math.floor(h / 24.0)) + include_offset
    norm_h = h % 24.0
    hh = int(norm_h)
    mm = int(round((norm_h - hh) * 60.0))
    if mm >= 60:
        hh = (hh + 1) % 24
        mm = 0
    time_str = f"{hh:02d}:{mm:02d}"
    if day_shift > 0:
        time_str += f" (+{day_shift})"
    elif day_shift < 0:
        time_str += f" ({day_shift})"
    return time_str

def resolve_timezone_info(tz_input: str, eval_dt: Optional[datetime] = None) -> Tuple[ZoneInfo, str, str, float]:
    """
    Dynamically resolve timezone identifier or abbreviation using current date
    to determine accurate standard/daylight offsets.
    Returns: (zone_info_obj, display_name, utc_offset_str, offset_hours)
    """
    if eval_dt is None:
        eval_dt = datetime.now(timezone.utc)

    cleaned = tz_input.strip().upper()

    # Explicit fixed offset (e.g. UTC+6, UTC-5, GMT+2)
    m_offset = re.match(r'^(?:UTC|GMT)\s*([+-])\s*(\d{1,2})(?::(\d{2}))?$', cleaned)
    if m_offset:
        sign = 1 if m_offset.group(1) == '+' else -1
        hrs = int(m_offset.group(2))
        mins = int(m_offset.group(3) or 0)
        delta_hrs = sign * (hrs + mins / 60.0)
        tz_offset = timezone(timedelta(hours=delta_hrs))
        off_str = f"UTC{m_offset.group(1)}{hrs:02d}:{mins:02d}" if mins else f"UTC{m_offset.group(1)}{hrs}"
        # We can represent it as ZoneInfo('UTC') with offset or timezone object
        return (ZoneInfo("UTC"), f"UTC {off_str}", off_str, delta_hrs)

    # IANA name direct or via abbreviation lookup
    iana_key = ABBREVIATION_TO_IANA.get(cleaned, tz_input.strip())
    
    try:
        zi = ZoneInfo(iana_key)
    except Exception:
        # Fallback if unknown
        if "DHAKA" in cleaned or "BANGLADESH" in cleaned or "BST" in cleaned:
            zi = ZoneInfo("Asia/Dhaka")
        elif "EASTERN" in cleaned or "EST" in cleaned or "EDT" in cleaned or "NEW YORK" in cleaned:
            zi = ZoneInfo("America/New_York")
        elif "PACIFIC" in cleaned or "PST" in cleaned or "PDT" in cleaned or "CALIFORNIA" in cleaned:
            zi = ZoneInfo("America/Los_Angeles")
        elif "CENTRAL" in cleaned or "CST" in cleaned or "CDT" in cleaned or "CHICAGO" in cleaned:
            zi = ZoneInfo("America/Chicago")
        elif "LONDON" in cleaned or "UK" in cleaned or "BRITISH" in cleaned:
            zi = ZoneInfo("Europe/London")
        elif "BERLIN" in cleaned or "GERMANY" in cleaned or "CET" in cleaned or "CEST" in cleaned:
            zi = ZoneInfo("Europe/Berlin")
        elif "INDIA" in cleaned or "IST" in cleaned:
            zi = ZoneInfo("Asia/Kolkata")
        elif "SINGAPORE" in cleaned or "SGT" in cleaned:
            zi = ZoneInfo("Asia/Singapore")
        else:
            zi = ZoneInfo("UTC")

    local_dt = eval_dt.astimezone(zi)
    offset_delta = local_dt.utcoffset() or timedelta(0)
    total_seconds = offset_delta.total_seconds()
    offset_hours = total_seconds / 3600.0
    
    sign_str = "+" if offset_hours >= 0 else "-"
    abs_hours = abs(offset_hours)
    h_part = int(abs_hours)
    m_part = int(round((abs_hours - h_part) * 60))
    offset_str = f"UTC{sign_str}{h_part}" if m_part == 0 else f"UTC{sign_str}{h_part}:{m_part:02d}"

    tz_abbr = local_dt.strftime("%Z")
    display_name = f"{iana_key.split('/')[-1].replace('_', ' ')} - {tz_abbr}"

    return (zi, display_name, offset_str, offset_hours)

class TimezoneFeasibilityEngine:
    """
    Production-grade Engine for cross-border time-zonefeasibility, circadian fatigue
    analysis, and exact overlap calculations.
    """

    def __init__(self, eval_date: Optional[datetime] = None):
        self.eval_date = eval_date or datetime.now(timezone.utc)

    def extract_job_timezone_requirements(self, text: str) -> Dict[str, Any]:
        """
        Intelligently parse unstructured job description text for timezone and overlap mentions.
        """
        extracted = {
            "required_overlap_hours": 4.0, # default
            "target_timezone": "America/New_York",
            "core_hours_start": "09:00",
            "core_hours_end": "17:00",
            "explicitly_mentioned": False
        }

        if not text:
            return extracted

        text_lower = text.lower()

        # 1. Overlap duration pattern (e.g. "at least 4 hours overlap", "4h overlap", "3-4 hours of overlap")
        overlap_match = re.search(r'(?:at least|minimum|require[ds]?|need)?\s*(\d+(?:\.\d+)?)\s*(?:-|to)?\s*(?:\d+)?\s*(?:hours?|hrs?)\s*(?:of\s*)?overlap', text_lower)
        if overlap_match:
            try:
                extracted["required_overlap_hours"] = float(overlap_match.group(1))
                extracted["explicitly_mentioned"] = True
            except Exception:
                pass

        # 2. Timezone abbreviation detection
        tz_patterns = [
            (r'\b(us\s*eastern|est|edt|et)\b', "America/New_York"),
            (r'\b(us\s*pacific|pst|pdt|pt)\b', "America/Los_Angeles"),
            (r'\b(us\s*central|cst|cdt|ct)\b', "America/Chicago"),
            (r'\b(us\s*mountain|mst|mdt|mt)\b', "America/Denver"),
            (r'\b(us\s*business\s*hours|us\s*hours)\b', "America/New_York"),
            (r'\b(cet|cest|central\s*european)\b', "Europe/Berlin"),
            (r'\b(eu\s*business\s*hours|european\s*hours)\b', "Europe/Berlin"),
            (r'\b(gmt|bst|uk\s*hours|london)\b', "Europe/London"),
            (r'\b(aest|aedt|australia[n]?\s*hours|sydney)\b', "Australia/Sydney"),
            (r'\b(sgt|singapore)\b', "Asia/Singapore"),
            (r'\b(jst|japan)\b', "Asia/Tokyo"),
            (r'\b(ist|india)\b', "Asia/Kolkata"),
            (r'\b(utc[+-]\d{1,2}|gmt[+-]\d{1,2})\b', None)
        ]

        for pat, iana_zone in tz_patterns:
            m = re.search(pat, text_lower)
            if m:
                extracted["explicitly_mentioned"] = True
                if iana_zone:
                    extracted["target_timezone"] = iana_zone
                else:
                    extracted["target_timezone"] = m.group(1).upper()
                break

        # 3. Core operating window (e.g. "9am - 5pm", "10:00 - 18:00")
        window_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:-|to)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:core|est|edt|pst|pdt|cet|gmt|hours)?', text_lower)
        if window_match:
            try:
                start_h = parse_time_str(window_match.group(1))
                end_h = parse_time_str(window_match.group(2))
                if 0 <= start_h < 24 and 0 < end_h <= 24:
                    extracted["core_hours_start"] = format_decimal_hour(start_h)
                    extracted["core_hours_end"] = format_decimal_hour(end_h)
            except Exception:
                pass

        return extracted

    def evaluate(
        self,
        candidate_timezone: str = "Asia/Dhaka",
        candidate_preferred_window: Tuple[str, str] = ("09:00", "18:00"),
        flexibility_tier: FlexibilityTier = FlexibilityTier.MODERATE_EVENING,
        employer_timezone: str = "America/New_York",
        employer_core_window: Tuple[str, str] = ("09:00", "17:00"),
        required_overlap_hours: float = 4.0,
        job_description_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute comprehensive Time-Zone & Working Hours Feasibility analysis.
        Adheres strictly to the requested JSON schema.
        """
        # If job description text provided, merge extracted context
        if job_description_text:
            parsed = self.extract_job_timezone_requirements(job_description_text)
            if parsed.get("explicitly_mentioned"):
                employer_timezone = parsed.get("target_timezone", employer_timezone)
                required_overlap_hours = parsed.get("required_overlap_hours", required_overlap_hours)
                employer_core_window = (parsed.get("core_hours_start", employer_core_window[0]),
                                        parsed.get("core_hours_end", employer_core_window[1]))

        # Dynamic timezone offset resolution
        _, cand_disp, cand_offset_str, cand_offset_hrs = resolve_timezone_info(candidate_timezone, self.eval_date)
        _, emp_disp, emp_offset_str, emp_offset_hrs = resolve_timezone_info(employer_timezone, self.eval_date)

        offset_delta_hrs = cand_offset_hrs - emp_offset_hrs

        # Decimal hours
        emp_start = parse_time_str(employer_core_window[0])
        emp_end = parse_time_str(employer_core_window[1])
        if emp_end <= emp_start:
            emp_end += 24.0 # Overnight shift

        cand_pref_start = parse_time_str(candidate_preferred_window[0])
        cand_pref_end = parse_time_str(candidate_preferred_window[1])
        if cand_pref_end <= cand_pref_start:
            cand_pref_end += 24.0

        # Employer core hours projected into candidate's local time
        emp_local_start = emp_start + offset_delta_hrs
        emp_local_end = emp_end + offset_delta_hrs

        # Maximum possible overlap between candidate (assuming 8h shift) and employer core hours (emp_end - emp_start)
        emp_core_duration = emp_end - emp_start
        max_possible_overlap = min(emp_core_duration, 8.0)

        # Standard natural overlap during candidate's preferred window (e.g. 09:00 - 18:00)
        # Normalize into candidate local reference day
        actual_overlap_standard = self._calculate_window_overlap(
            cand_pref_start, cand_pref_end,
            emp_local_start, emp_local_end
        )

        # Minimum shift calculation to satisfy required overlap
        # Check candidate limits based on flexibility tier
        max_allowed_end = 20.0 # STRICT_DAYLIGHT
        min_allowed_start = 8.0
        if flexibility_tier == FlexibilityTier.MODERATE_EVENING:
            max_allowed_end = 24.0 # up to midnight
        elif flexibility_tier == FlexibilityTier.NIGHT_OWL:
            max_allowed_end = 31.0 # 07:00 next day (24 + 7)

        # Find recommended overlap window in candidate local time
        recommended_overlap_local, actual_satisfying_overlap, shifts_into_night, latest_work_hour = (
            self._project_recommended_schedule(
                emp_local_start=emp_local_start,
                emp_local_end=emp_local_end,
                pref_start=cand_pref_start,
                pref_end=cand_pref_end,
                req_hours=required_overlap_hours,
                max_allowed_end=max_allowed_end,
                flexibility=flexibility_tier
            )
        )

        # Feasibility & Fatigue Classification
        # 1. OPTIMAL (Normal Day): Overlap satisfied between 08:00 and 19:00 local time
        # 2. MANAGEABLE (Evening Shift): Overlap requires working between 19:00 and 23:30 local time
        # 3. EXTREME (Night Shift): Overlap forces working between 23:30 and 06:00 local time
        # 4. INCOMPATIBLE: Cannot satisfy overlap within allowed tier or >12h work
        if actual_satisfying_overlap < required_overlap_hours:
            status = FeasibilityStatus.INCOMPATIBLE
            score = max(5, int((actual_satisfying_overlap / max(1.0, required_overlap_hours)) * 30))
            badge_variant = "destructive"
            tag_label = "Incompatible Schedule"
            plain_summary = (
                f"Requires {required_overlap_hours}h overlap with {emp_disp}, but only "
                f"{round(actual_satisfying_overlap, 1)}h overlap is achievable within your {flexibility_tier.value} constraints."
            )
        elif latest_work_hour <= 19.0 and not shifts_into_night:
            status = FeasibilityStatus.OPTIMAL
            score = 95
            badge_variant = "success"
            tag_label = "Optimal Day Schedule"
            plain_summary = (
                f"Full daytime alignment ({emp_disp}). Your {required_overlap_hours}h overlap requirement "
                f"fits comfortably within daytime hours ({recommended_overlap_local}) with zero circadian disruption."
            )
        elif latest_work_hour <= 23.5:
            if flexibility_tier == FlexibilityTier.STRICT_DAYLIGHT:
                status = FeasibilityStatus.INCOMPATIBLE
                score = 25
                badge_variant = "destructive"
                tag_label = "Requires Evening Shift"
                plain_summary = (
                    f"Requires working evening hours ({recommended_overlap_local}), which conflicts with your "
                    f"STRICT_DAYLIGHT preference (max 20:00)."
                )
            else:
                status = FeasibilityStatus.MANAGEABLE
                score = 78
                badge_variant = "warning"
                tag_label = "Manageable Evening Overlap"
                plain_summary = (
                    f"Manageable evening shift. Satisfies {required_overlap_hours}h overlap by working "
                    f"in the evening ({recommended_overlap_local}). Ideal for flexible candidates."
                )
        else: # forces 23:30 to 06:00
            if flexibility_tier != FlexibilityTier.NIGHT_OWL:
                status = FeasibilityStatus.INCOMPATIBLE
                score = 15
                badge_variant = "destructive"
                tag_label = "Incompatible Night Shift"
                plain_summary = (
                    f"Forces late night / graveyard working ({recommended_overlap_local}) until {format_decimal_hour(latest_work_hour)}, "
                    f"exceeding your current flexibility tier."
                )
            else:
                status = FeasibilityStatus.EXTREME
                score = 45
                badge_variant = "destructive"
                tag_label = "Extreme Night Shift"
                plain_summary = (
                    f"Extreme graveyard/night shift schedule ({recommended_overlap_local}). Requires inverted sleep "
                    f"pattern to overlap with {emp_disp}."
                )

        # Timeline Bar 24h slices (in 0-24 hour scale)
        norm_rec_start = (emp_local_start) % 24.0
        norm_rec_end = (emp_local_start + actual_satisfying_overlap) % 24.0
        
        # Calculate local work slice (standard 8-hour window shifted to encompass overlap)
        local_work_start = max(cand_pref_start, emp_local_start - (8.0 - actual_satisfying_overlap))
        local_work_start = max(0.0, min(16.0, local_work_start))
        local_work_end = (local_work_start + 8.0) % 24.0

        # Construct candidate equivalent core hours string
        cand_eq_str = f"{format_decimal_hour(emp_local_start)} - {format_decimal_hour(emp_local_end)} {cand_disp.split(' - ')[-1]}"
        emp_core_str = f"{employer_core_window[0]} - {employer_core_window[1]} {emp_disp.split(' - ')[-1]}"

        return {
            "feasibility_status": status.value,
            "match_score": score,
            "metrics": {
                "required_overlap_hours": float(required_overlap_hours),
                "actual_overlap_hours_standard": round(actual_overlap_standard, 1),
                "max_possible_overlap_hours": round(max_possible_overlap, 1)
            },
            "zones": {
                "employer_zone": emp_disp,
                "employer_offset": emp_offset_str,
                "candidate_zone": candidate_timezone,
                "candidate_offset": cand_offset_str,
                "offset_delta_hours": round(offset_delta_hrs, 1)
            },
            "schedule_projection": {
                "employer_core_hours": emp_core_str,
                "candidate_equivalent_hours": cand_eq_str,
                "recommended_overlap_window_local": f"{recommended_overlap_local} {cand_disp.split(' - ')[-1]}",
                "shifts_into_night": bool(shifts_into_night)
            },
            "ui_render_data": {
                "tag_label": tag_label,
                "badge_variant": badge_variant,
                "timeline_bar_24h": {
                    "local_work_slice": [round(local_work_start, 1), round(local_work_end, 1)],
                    "overlap_slice": [round(norm_rec_start, 1), round(norm_rec_end, 1)],
                    "night_hours_slice": [22.0, 6.0]
                },
                "plain_english_summary": plain_summary
            }
        }

    def _calculate_window_overlap(self, s1: float, e1: float, s2: float, e2: float) -> float:
        """Calculate overlap hours between two intervals, accounting for possible day boundary shifts."""
        max_overlap = 0.0
        # Check alignment across current day, previous day (-24), and next day (+24)
        for offset in [-24.0, 0.0, 24.0]:
            shift_s2 = s2 + offset
            shift_e2 = e2 + offset
            
            inter_start = max(s1, shift_s2)
            inter_end = min(e1, shift_e2)
            if inter_end > inter_start:
                max_overlap = max(max_overlap, inter_end - inter_start)
        return max_overlap

    def _project_recommended_schedule(
        self,
        emp_local_start: float,
        emp_local_end: float,
        pref_start: float,
        pref_end: float,
        req_hours: float,
        max_allowed_end: float,
        flexibility: FlexibilityTier
    ) -> Tuple[str, float, bool, float]:
        """
        Determine optimal overlap window minimizing circadian stress while fulfilling req_hours.
        Returns: (window_str, achieved_overlap, shifts_into_night, latest_hour)
        """
        # Align employer window closest to the candidate's active day
        norm_start = emp_local_start
        norm_end = emp_local_end
        
        while norm_start < 6.0:
            norm_start += 24.0
            norm_end += 24.0
        while norm_start > 30.0:
            norm_start -= 24.0
            norm_end -= 24.0

        # Best overlap candidate slice: start as early as employer is available
        overlap_start = norm_start
        overlap_end = min(norm_end, overlap_start + req_hours)
        achieved = max(0.0, overlap_end - overlap_start)

        # Check if latest hour violates candidate flexibility
        latest_hour = overlap_end
        shifts_into_night = (latest_hour > 22.0 or (latest_hour % 24.0) < 6.0)

        # If achieved is less than required, candidate can't satisfy even with full duration
        if achieved > req_hours:
            achieved = req_hours

        # If latest hour exceeds allowed end for tier:
        if latest_hour > max_allowed_end:
            # Overlap constrained by flexibility
            achieved = max(0.0, min(achieved, max_allowed_end - overlap_start))

        window_str = f"{format_decimal_hour(overlap_start)} - {format_decimal_hour(overlap_start + achieved)}"
        return (window_str, achieved, shifts_into_night, latest_hour)

# Global singleton instance
feasibility_engine = TimezoneFeasibilityEngine()
