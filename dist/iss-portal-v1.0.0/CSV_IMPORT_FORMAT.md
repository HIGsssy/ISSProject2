# CSV Import Format Documentation

## Overview
This document describes the CSV file format for bulk importing child records into the ISS Portal.

## File Requirements
- **Format:** CSV (Comma-Separated Values)
- **Encoding:** UTF-8
- **Maximum Size:** 10MB (~5000 records)
- **Date Format:** YYYY-MM-DD (e.g., 2015-03-15)
- **Boolean Values:** true/false, yes/no, 1/0 (case-insensitive)

## Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `first_name` | Child's first name | John |
| `last_name` | Child's last name | Smith |
| `date_of_birth` | Date of birth in YYYY-MM-DD format | 2015-03-15 |

## Optional Fields

### Centre Assignment
| Field | Description | Example |
|-------|-------------|---------|
| `centre` | Centre name (must match existing centre exactly) | Main Centre |
| `start_date` | Start date in YYYY-MM-DD format | 2024-01-01 |
| `on_hold` | Whether child is on hold (true/false) | false |

### Address Information
| Field | Description | Example |
|-------|-------------|---------|
| `address_line1` | Street address | 123 Main St |
| `address_line2` | Apartment/unit number | Unit 10 |
| `city` | City name | Toronto |
| `province` | Province/state code | ON |
| `postal_code` | Postal/zip code | M1A 1A1 |
| `alternate_location` | Alternate address or notes | Lives with grandmother at same address |

### Guardian 1 Information
| Field | Description | Example |
|-------|-------------|---------|
| `guardian1_name` | Full name | Sarah Smith |
| `guardian1_home_phone` | Home phone number | 416-555-0100 |
| `guardian1_work_phone` | Work phone number | 416-555-0101 |
| `guardian1_cell_phone` | Cell/mobile phone number | 647-555-0102 |
| `guardian1_email` | Email address | sarah@example.com |

### Guardian 2 Information
| Field | Description | Example |
|-------|-------------|---------|
| `guardian2_name` | Full name | John Smith |
| `guardian2_home_phone` | Home phone number | 416-555-0200 |
| `guardian2_work_phone` | Work phone number | 416-555-0201 |
| `guardian2_cell_phone` | Cell/mobile phone number | 647-555-0202 |
| `guardian2_email` | Email address | john@example.com |

### Referral Source
| Field | Description | Example |
|-------|-------------|---------|
| `referral_source_type` | Type of referral: `parent_guardian` or `other_agency` | parent_guardian |
| `referral_source_name` | Name of referring person | Dr. Sarah Johnson |
| `referral_source_phone` | Phone number of referrer | 416-555-4000 |
| `referral_agency_name` | Agency name (if other_agency) | Community Health Services |
| `referral_agency_address` | Agency address | 100 Medical Drive, Toronto ON |

### Referral Reasons (Boolean Fields)
All fields accept true/false, yes/no, 1/0, or can be left empty (defaults to false).

| Field | Description |
|-------|-------------|
| `referral_reason_cognitive` | Cognitive development concerns |
| `referral_reason_language` | Language/communication concerns |
| `referral_reason_gross_motor` | Gross motor skills concerns |
| `referral_reason_fine_motor` | Fine motor skills concerns |
| `referral_reason_social_emotional` | Social/emotional development concerns |
| `referral_reason_self_help` | Self-help skills concerns |
| `referral_reason_other` | Other concerns |
| `referral_reason_details` | Free text description of concerns | Concerns with speech development |

### Program Attendance

#### Childcare
| Field | Description | Example |
|-------|-------------|---------|
| `attends_childcare` | Whether child attends childcare (true/false) | true |
| `childcare_centre` | Childcare centre name (must match existing centre) | ABC Childcare |
| `childcare_frequency` | How often child attends | Full-time |

#### EarlyON
| Field | Description | Example |
|-------|-------------|---------|
| `attends_earlyon` | Whether child attends EarlyON (true/false) | true |
| `earlyon_centre` | EarlyON centre name (must match existing centre) | Downtown EarlyON |
| `earlyon_frequency` | How often child attends | Weekly |

### Additional Referral Details
| Field | Description | Example |
|-------|-------------|---------|
| `agency_continuing_involvement` | Whether agency is continuing involvement (true/false) | true |
| `referral_consent_on_file` | Whether consent form is on file (true/false) | true |

### Other Fields
| Field | Description | Example |
|-------|-------------|---------|
| `notes` | General notes about the child | Parent referred |
| `end_date` | End/discharge date (YYYY-MM-DD) | 2024-12-31 |
| `discharge_reason` | Reason for discharge | Moved out of area |

## Important Notes

1. **Centre Names Must Match:** Centre names in the `centre`, `childcare_centre`, and `earlyon_centre` fields must exactly match existing centre names in the system (case-insensitive).

2. **Duplicate Detection:** The system will detect potential duplicates based on matching first name, last name, and date of birth.

3. **Default Status:** All imported children will have:
   - `overall_status`: active
   - `caseload_status`: awaiting_assignment
   
4. **Data Encryption:** All personal information (PII) is automatically encrypted when imported.

5. **Phone Number Migration:** If you have old CSV files with `guardian1_phone` or `guardian2_phone` fields, the system will no longer accept these. You must split them into separate `home_phone`, `work_phone`, and `cell_phone` fields.

6. **Boolean Value Flexibility:** Boolean fields accept multiple formats:
   - True values: `true`, `yes`, `y`, `1` (case-insensitive)
   - False values: `false`, `no`, `n`, `0`, or empty string

## Example CSV Structure

### Minimal Import (Required Fields Only)
```csv
first_name,last_name,date_of_birth
John,Smith,2015-03-15
Jane,Doe,2016-07-22
```

### Basic Import with Guardian Info
```csv
first_name,last_name,date_of_birth,centre,guardian1_name,guardian1_cell_phone,guardian1_email
John,Smith,2015-03-15,Main Centre,Sarah Smith,647-555-0102,sarah@example.com
Jane,Doe,2016-07-22,,John Doe,647-555-0456,john@example.com
```

### Complete Import with All Fields
See the downloaded template CSV for a complete example with all available fields.

## Getting the Template

Download the CSV template from the Import page in the ISS Portal. The template includes:
- All available column headers in the correct order
- Three example rows demonstrating different scenarios:
  1. Minimal data (required fields only)
  2. Parent/guardian referral with basic intake info
  3. Agency referral with complete details

## Validation and Errors

The import process includes two stages:

1. **Validation:** Your CSV will be validated before import. Common errors include:
   - Missing required fields
   - Invalid date formats
   - Invalid email addresses
   - Centre names that don't exist
   - Invalid referral_source_type values
   - Date of birth in the future or too old (>25 years)

2. **Preview:** After validation, you'll see a preview of all records that will be imported, along with any errors or warnings.

3. **Import:** Only valid records will be imported. You can choose to skip or overwrite duplicates.

## Best Practices

1. **Start with the Template:** Always download and use the provided CSV template to ensure correct column names and order.

2. **Test with Small Files:** Test your import process with a small file (5-10 records) before importing large batches.

3. **Check Centre Names:** Verify that all centre names in your CSV exactly match the names in the system.

4. **Use Descriptive Notes:** Include helpful notes in the `notes` field for future reference.

5. **Complete Data:** While most fields are optional, more complete records are more useful. Include as much information as available.

6. **UTF-8 Encoding:** Ensure your CSV file is saved with UTF-8 encoding, especially if it contains special characters or accents.

## Troubleshooting

**Q: My import shows "Centre not found" errors**  
A: Check that the centre name in your CSV exactly matches the name in the system. Centre lookups are case-insensitive but must match exactly otherwise.

**Q: I have old CSVs with guardian1_phone instead of the split phone fields**  
A: You'll need to update your CSV to use the new field names: `guardian1_home_phone`, `guardian1_work_phone`, `guardian1_cell_phone`. If you only have one phone number, put it in the most appropriate field (usually `guardian1_cell_phone`).

**Q: Can I leave optional fields empty?**  
A: Yes, you can leave any optional field empty. The system will only import the fields that have values.

**Q: What happens to duplicates?**  
A: The system will detect potential duplicates (same name and DOB) and let you choose to skip them or import anyway during the preview stage.

**Q: Can I import discharged children?**  
A: While you can include `end_date` and `discharge_reason` fields, it's recommended to discharge children through the discharge workflow in the application for proper tracking. All imports default to "active" status.
