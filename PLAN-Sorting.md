# Plan: "New to Program" Badge + Date Added & Sorting

Two features: a **"New" badge** on child records (visible for 30 days from add date, across all child listing views), and **date added display + clickable sort headers** on the all_children page.

---

## Phase 1 — "New to Program" Badge

### Step 1: Add `is_new_to_program` property to Child model
- **File:** `core/models.py` (~line 266, after existing properties like `get_primary_staff()`)
- **Logic:** `(timezone.now() - self.created_at).days <= 30`
- No migration needed — it's a computed property

### Step 2: Add CSS for the badge
- **File:** `static/css/custom.css` — add `.new-to-program-badge` after the `.on-hold-badge` rule
- **Styling:** Distinct teal/cyan (bg `#ccfbf1`, text `#0f766e`, border `#14b8a6`) to differentiate from existing badges

### Step 3: Add badge to all three child listing templates
Add `{% if child.is_new_to_program %}<span class="... new-to-program-badge">New</span>{% endif %}` after the "On Monitor" badge block in each template:

- **`templates/core/all_children.html`** — in the `<div class="flex gap-2">` badge group (~line 139)
- **`templates/core/my_caseload.html`** — in the `<div class="flex flex-col gap-1">` badge group (~line 73)
- **`templates/core/non_caseload_children.html`** — in the `<div class="flex flex-col gap-1">` badge group (~line 49)

### Step 4: Add "New to Program" filter to all_children view
- **File:** `core/views.py` in `all_children()` — add `new_to_program` GET param (`all`/`yes`/`no`)
- **Logic:** If `yes`, filter `created_at >= now - 30 days`; if `no`, filter `created_at < now - 30 days`
- Pass `new_to_program_filter` to template context
- **File:** `templates/core/all_children.html` — add corresponding dropdown in the filter form

---

## Phase 2 — Date Added Display + Sorting (all_children only)

### Step 5: Add sort parameter to all_children view
- **File:** `core/views.py` in `all_children()` — read `sort` GET param
- **Values:** `name_az` (default), `date_newest` (`-created_at`), `date_oldest` (`created_at`)
- Apply `.order_by()` to the queryset before pagination
- Pass `sort` value to template context

### Step 6: Add clickable column headers + date display to all_children.html
- **File:** `templates/core/all_children.html`
- Add a header bar above the child list with **"Name"** and **"Date Added"** as clickable links
- Each header link preserves current filter/search params and sets the `sort` value
- Show `{{ child.created_at|date:"M d, Y" }}` in each child row alongside existing info (Age, Centre, Primary Staff)

---

## Files to Modify

| File | Changes |
|------|---------|
| `core/models.py` | Add `is_new_to_program` property on `Child` class |
| `static/css/custom.css` | Add `.new-to-program-badge` style |
| `core/views.py` | Modify `all_children()`: add `new_to_program` filter + `sort` parameter |
| `templates/core/all_children.html` | Badge, filter dropdown, date display, sort column headers |
| `templates/core/my_caseload.html` | Badge only |
| `templates/core/non_caseload_children.html` | Badge only |

---

## Verification

1. Find/create a child added within the last 30 days — confirm "New" badge appears on all three listing pages
2. Confirm a child added 31+ days ago does NOT show the badge
3. Use the "New to Program" filter on all_children — confirm it correctly includes/excludes children
4. Click "Date Added" header — confirm sort by newest first, then oldest first on second click
5. Click "Name" header — confirm sort returns to alphabetical
6. Confirm existing filters (search, status, staff, on monitor) all work alongside sorting
7. Confirm pagination preserves both filter and sort params in URLs
