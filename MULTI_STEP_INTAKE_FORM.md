# Multi-Step Intake Form - Implementation Summary

## Overview
A complete 5-step wizard interface for adding new children to the ISS Portal system. Replaces the previous single-page form with a guided intake process that matches the PDF intake form structure.

## Features Implemented

### 1. Progress Indicator
- Visual step tracker showing current position (1-5)
- Progress bars connecting steps
- Color-coded states:
  - **Blue**: Active step
  - **Green**: Completed steps
  - **Gray**: Upcoming steps

### 2. Five-Step Workflow

#### Step 1: Child Information
- First Name * (required)
- Last Name * (required)
- Date of Birth * (required)
- Address Line 1
- Address Line 2
- City/Town
- Postal Code
- Alternate Location (if different than mailing address)

#### Step 2: Guardian Information
- **Guardian 1:**
  - Full Name
  - Home Phone
  - Work Phone
  - Cell Phone
  - Email
- **Guardian 2 (Optional):**
  - Full Name
  - Home Phone
  - Work Phone
  - Cell Phone
  - Email

#### Step 3: Referral Information
- Referred By * (required radio button):
  - Parent/Guardian
  - Other Agency (shows additional fields)
- Contact Name
- Contact Phone
- Agency Name (conditional on "Other Agency")
- Agency Address (conditional on "Other Agency")
- **Reason for Referral** (checkboxes):
  - Cognitive
  - Language
  - Gross Motor
  - Fine Motor
  - Social/Emotional
  - Self-help
  - Other
- Details about referral reasons (textarea)

#### Step 4: Program Attendance
- **Licensed Child Care:**
  - Checkbox: Is child attending?
  - Centre selector (if yes)
  - Frequency (if yes)
- **EarlyON Child and Family Center:**
  - Checkbox: Is child attending?
  - Centre selector (if yes)
  - Frequency (if yes)
- Referring agency continuing involvement (checkbox)

#### Step 5: Review & Submit
- Summary display of all entered information
- Organized by sections (Child Info, Guardians, Referral, Programs)
- **Required:** Referral consent form on file (checkbox)
- Submit button (green)

### 3. Form Navigation
- **Previous Button:** Go back to any step (hidden on step 1)
- **Next Button:** Advance to next step (validates required fields)
- **Cancel Button:** Return to children list
- **Submit Button:** Only visible on step 5

### 4. Form Validation
- Required field checking before advancing steps
- Visual feedback (red borders) for invalid fields
- Alert message if validation fails
- Email format validation
- Date format validation

### 5. Conditional Field Display
- Agency fields only shown when "Other Agency" selected
- Childcare details only shown when checkbox checked
- EarlyON details only shown when checkbox checked

### 6. API Integration
- Form submits via `/api/children/` POST endpoint
- Sends all 31 new intake fields plus existing fields
- Handles checkbox to boolean conversion
- Properly handles null/empty values
- Sets default status:
  - `overall_status`: 'active'
  - `caseload_status`: 'awaiting_assignment'
- Redirects to child detail page on success

## Technical Implementation

### Files Modified

#### `templates/core/add_child.html` (Completely Replaced)
- New multi-step wizard template
- Progress indicator with 5 steps
- All form steps with proper field names matching model
- JavaScript for step navigation and validation
- CSS for step indicator styling
- Form submission handling with AJAX

#### `core/serializers.py` (Updated)
**ChildCreateSerializer** - Added all new fields:
- `alternate_location`
- Guardian phone splits: `guardian1_home_phone`, `guardian1_work_phone`, `guardian1_cell_phone`
- Guardian 2 phone splits: `guardian2_home_phone`, `guardian2_work_phone`, `guardian2_cell_phone`
- Referral fields: `referral_source_type`, `referral_source_name`, `referral_source_phone`, `referral_agency_name`, `referral_agency_address`
- Referral reason booleans: `referral_reason_cognitive`, `referral_reason_language`, `referral_reason_gross_motor`, `referral_reason_fine_motor`, `referral_reason_social_emotional`, `referral_reason_self_help`, `referral_reason_other`
- `referral_reason_details` (encrypted textarea)
- Childcare: `attends_childcare`, `childcare_centre`, `childcare_frequency`
- EarlyON: `attends_earlyon`, `earlyon_centre`, `earlyon_frequency`
- `agency_continuing_involvement`, `referral_consent_on_file`
- `overall_status`, `discharge_reason`

### API Endpoint
Uses existing `/api/children/` POST endpoint:
- **ViewSet:** `ChildViewSet` in `core/viewsets.py`
- **Serializer:** `ChildCreateSerializer`
- **Permissions:** Staff, Supervisor, Admin (but view restricted to Supervisor/Admin in templates)

### JavaScript Features
1. **showStep(step)** - Displays specific step and updates UI
2. **validateStep(step)** - Validates required fields before advancing
3. **populateReview()** - Generates summary on step 5
4. **Event Listeners:**
   - Referral type toggle (show/hide agency fields)
   - Childcare toggle (show/hide centre/frequency)
   - EarlyON toggle (show/hide centre/frequency)
   - Next/Previous button handlers
   - Form submit handler (AJAX)

### Styling (CSS)
- `.step-circle` - Circular step indicators (36px)
- `.step-indicator.active` - Blue for current step
- `.step-indicator.completed` - Green for completed steps
- `.form-step` - Hidden by default
- `.form-step.active` - Visible step
- Progress bars with smooth width transitions

## Data Flow

1. **User fills step 1** → Clicks "Next"
2. **JavaScript validates** → Shows step 2 if valid
3. **Repeat for steps 2-4** → Advance through wizard
4. **Step 5 generates review** → `populateReview()` displays summary
5. **User confirms consent** → Clicks "Submit"
6. **JavaScript collects all data** → Builds JSON object
7. **AJAX POST to `/api/children/`** → Creates child record
8. **Success response** → Redirect to child detail page
9. **Error response** → Show alert with error details

## Field Mapping (Form → Database)

All form field names match the Child model field names exactly:
- Text inputs → EncryptedCharField or CharField
- Textareas → EncryptedTextField
- Checkboxes → BooleanField
- Radio buttons → CharField with choices
- Select dropdowns → ForeignKey (Centre model)
- Date inputs → DateField

## Access Control
- **View restriction:** Only Supervisor and Admin users see "Add Child" button (staff users cannot access)
- **URL restriction:** `add_child` view checks `user.role in ['supervisor', 'admin']`
- **Template permission:** Conditional rendering in dashboard, all_children, my_caseload
- **API permission:** `IsStaffMember` (but effectively Supervisor/Admin only via view restriction)

## Testing Checklist

✅ **Navigation:**
- [ ] Progress indicator updates correctly
- [ ] Previous button works (goes back)
- [ ] Next button advances (with validation)
- [ ] Submit button only on step 5
- [ ] Cancel returns to children list

✅ **Validation:**
- [ ] Step 1 requires: first_name, last_name, date_of_birth, referral_source_type
- [ ] Email fields validate format
- [ ] Date field validates format
- [ ] Cannot advance without required fields

✅ **Conditional Fields:**
- [ ] Agency fields show when "Other Agency" selected
- [ ] Childcare fields show when checkbox checked
- [ ] EarlyON fields show when checkbox checked

✅ **Data Submission:**
- [ ] All fields submit correctly
- [ ] Checkboxes convert to boolean true/false
- [ ] Empty fields sent as empty string or null
- [ ] Child created with correct status
- [ ] Redirect to child detail page works

✅ **Encryption:**
- [ ] PII fields encrypted in database
- [ ] Guardian phones encrypted
- [ ] Addresses encrypted
- [ ] Referral details encrypted

## Future Enhancements (Phase 5 - Reporting)
1. Age out statistics (children 13+)
2. Month added tracking reports
3. Staff site visit view
4. Site visit reports
5. Enhanced caseload analytics

## Notes
- Form template replaces old single-page add_child.html completely
- Serializer updated to accept all 31 new intake fields
- No changes needed to viewsets.py (already had ChildCreateSerializer)
- Templates volume-mounted in dev, but need rebuild for Docker image
- All encrypted fields automatically handled by django-encrypted-model-fields
