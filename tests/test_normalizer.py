import pytest
from core.normalizer import parse_salary, parse_experience, parse_date, classify_company_tier

def test_parse_salary_disclosed_range():
    s = parse_salary("Tk. 25000 - 35000 (Monthly)")
    assert s.disclosed is True
    assert s.min_salary == 25000.0
    assert s.max_salary == 35000.0
    assert s.currency == "BDT"
    assert s.period == "Monthly"

def test_parse_salary_single_value_with_commas():
    s = parse_salary("BDT 80,000 per month")
    assert s.disclosed is True
    assert s.min_salary == 80000.0
    assert s.max_salary == 80000.0

def test_parse_salary_negotiable():
    s = parse_salary("Negotiable")
    assert s.disclosed is False
    assert s.min_salary is None

def test_parse_salary_empty_or_dash():
    s = parse_salary("--")
    assert s.disclosed is False

def test_parse_experience_range():
    e = parse_experience("4 to 8 years")
    assert e.min_years == 4.0
    assert e.max_years == 8.0

def test_parse_experience_fresher():
    e = parse_experience("Fresher can apply")
    assert e.min_years == 0.0
    assert e.max_years == 1.0

def test_parse_experience_minimum():
    e = parse_experience("At least 3 year(s)")
    assert e.min_years == 3.0
    assert e.max_years is None

def test_company_tier_classification():
    assert classify_company_tier("British American Tobacco Bangladesh") == "MNC"
    assert classify_company_tier("BRAC Bank Limited") == "Financial Institution"
    assert classify_company_tier("Square Pharmaceuticals Ltd.") == "Conglomerate"
    assert classify_company_tier("A leading Group of Companies") == "Confidential"
    assert classify_company_tier("Akota Landmark Ltd") == "Corporate"
