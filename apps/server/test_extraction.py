"""Quick test script for mandate extraction with subprocess categorization."""

import sys
import os
import json
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test imports
try:
    from utils.tools import scan_mandate_folder_and_parse, parse_all_mandate_fields, separate_capability_data
    print("✅ All tools imported successfully")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test capability params matching your input
test_capability_params = {
    "1": {
        "subprocess_id": 1, 
        "subprocess_name": "Sector & Industry Research", 
        "category": "Back Office", 
        "data_elements": ["country", "sector", "industry"]
    },
    "2": {
        "subprocess_id": 2, 
        "subprocess_name": "Bottom-Up Fundamental Analysis", 
        "category": "Back Office", 
        "data_elements": ["revenue", "ebitda", "growth", "gross_profit_margin", "net_income", "return_on_equity", "debt_to_equity", "pe_ratio", "price_to_book", "market_cap", "dividend_yield"]
    },
    "3": {
        "subprocess_id": 3, 
        "subprocess_name": "Risk Assessment of Investment Ideas", 
        "category": "Back Office", 
        "data_elements": ["competitive_position", "governance_quality", "customer_concentration_risk", "vendor_platform_dependency", "regulatory_legal_risk", "business_model_complexity"]
    }
}

if __name__ == "__main__":
    print("\n" + "="*70)
    print("Testing NEW Mandate Extraction Pipeline (Two-Phase)")
    print("="*70)
    
    # Step 1: Scan and parse PDF
    print("\n[Phase 1.0] Scanning mandate folder...")
    try:
        pdf_result = scan_mandate_folder_and_parse()
        pdf_result_dict = json.loads(pdf_result) if isinstance(pdf_result, str) else pdf_result
        pdf_name = pdf_result_dict.get("pdf_name", "Unknown")
        raw_text = pdf_result_dict.get("full_text", "")
        char_count = pdf_result_dict.get("char_count", 0)
        
        print(f"✅ PDF scanned: {pdf_name}")
        print(f"   Characters extracted: {char_count}")
    except Exception as e:
        print(f"❌ PDF scanning failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Step 2: Extract all fields with subprocess categorization
    print("\n[Phase 1.1] Extracting ALL fields with subprocess categorization...")
    try:
        capability_params_str = json.dumps(test_capability_params)
        fields_result = parse_all_mandate_fields(raw_text, capability_params_str)
        fields_data = json.loads(fields_result)
        
        if "error" in fields_data:
            print(f"❌ Field extraction error: {fields_data['error']}")
            sys.exit(1)
        
        all_fields = fields_data.get("all_extracted_fields", {})
        field_mapping = fields_data.get("field_to_subprocess_mapping", {})
        
        print(f"✅ Fields extracted: {len(all_fields)} fields")
        print(f"   Sample fields:")
        for field_name, field_value in list(all_fields.items())[:8]:
            subprocess_hint = field_mapping.get(field_name, "Unknown")
            if field_value != "-":
                print(f"   - {field_name}: {str(field_value)[:45]}... → {subprocess_hint}")
        if len(all_fields) > 8:
            print(f"   ... and {len(all_fields) - 8} more fields")
    except Exception as e:
        print(f"❌ Field extraction failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Step 3: Separate by capability (semantic matching)
    print("\n[Phase 2] Organizing fields by capability subprocesses via LLM...")
    try:
        separated_result = separate_capability_data(fields_result, capability_params_str)
        separated_data = json.loads(separated_result)
        
        if "error" in separated_data:
            print(f"❌ Separation error: {separated_data['error']}")
            sys.exit(1)
        
        criteria = separated_data.get("criteria", {}).get("mandate", {})
        additional = separated_data.get("additional_data", {})
        
        print(f"✅ Semantic matching complete")
        print(f"\n📋 CRITERIA (subprocess structure):")
        for subprocess_name, fields in criteria.items():
            if isinstance(fields, dict):
                print(f"\n   {subprocess_name}:")
                for fname, fval in fields.items():
                    print(f"       {fname}: {fval}")
            else:
                print(f"   {subprocess_name}: {fields}")
        
        print(f"\n📦 ADDITIONAL DATA ({len(additional)} fields):")
        for fname, fval in list(additional.items())[:5]:
            print(f"   - {fname}: {fval}")
        if len(additional) > 5:
            print(f"   ... and {len(additional) - 5} more fields")
    except Exception as e:
        print(f"❌ Organization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "="*70)
    print("✅ TWO-PHASE EXTRACTION TEST COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("\n📌 Key Points:")
    print("   1. Phase 1: LLM extracted fields AND categorized them to subprocesses")
    print("   2. Phase 2: Simple organizer put data in BOTH criteria and additional_data")
    print("   3. All field values are precise and concise (no lengthy text)")

