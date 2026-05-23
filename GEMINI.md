# GEMINI.md - PUPuni-CAMS Project Context

## Project Overview
**PUPuni-CAMS** (PUP Campus Activity Management System) is a Django-based platform designed to manage student organization activities at PUP. It streamlines the lifecycle of campus events from proposal and multi-stage approval to attendance tracking and analytics.

### Main Technologies
- **Backend:** Django 6.0.3
- **Database:** SQLite3
- **Document Generation:** `docxtpl` (Python-docx-template) for generating official letters from `.docx` templates.
- **Email:** Gmail SMTP (`pupunicams@gmail.com`) for account verification and notifications.
- **Frontend:** Vanilla CSS/JS with role-specific templates and Tailwind-like utility classes.

### Core Architecture
The project uses a standard Django MVT architecture with a custom Role-Based Access Control (RBAC) system defined in `campus_app/views.py`.

#### User Roles:
- **Admin:** Superusers who handle final approvals and system-wide account management.
- **Adviser:** Staff members (not superusers) who provide faculty oversight and verify documents.
- **Organizer:** Student leaders who create event proposals and manage their organization's members.
- **Student:** General users who register, attend events, and provide feedback.

---

## Building and Running

### Prerequisites
- Python 3.x
- Virtual Environment (`venv`)

### Commands
- **Install Dependencies:** `pip install -r requirements.txt`
- **Database Migrations:** 
  - `python manage.py makemigrations`
  - `python manage.py migrate`
- **Run Development Server:** `python manage.py runserver`
- **Create Superuser (Admin):** `python manage.py createsuperuser`

---

## Development Conventions

### 1. 6-Step Approval Workflow
All events must pass through these states in order:
1. `Pending Adviser`: Initial review by the Org Adviser.
2. `Pending Admin`: Initial clearance by the Admin office.
3. `Admin Approved`: Permission to print and gather manual signatures.
4. `Permit Verification`: Adviser verifies the uploaded signed documents.
5. `Final Admin Review`: Admin gives final clearance for publication.
6. `Approved`: Event is live and visible to students.

### 2. RBAC Guards
Always use the strict RBAC decorators in `views.py` when adding new endpoints:
- `is_admin_strictly`: `user.is_superuser`
- `is_adviser_strictly`: `user.is_staff and not is_superuser`
- `is_organizer_strictly`: `OrgProfile` existence check.
- `is_student_strictly`: `Student` existence check.

### 3. Attendance Validation
The `Attendance` model and student portal use two layers of validation:
- **Geofencing:** Compares student's `latitude/longitude` against the event's `target_latitude/longitude`.
- **Face Matching:** Verifies the student's face against the stored `face_encoding`.
- Both flags (`face_matched`, `is_valid_location`) must be tracked for valid attendance.

### 4. Evaluation & Analytics
- **Evaluation:** Currently implemented as a frontend-heavy feature using `LocalStorage` and session storage to simulate the "Evaluation Hub".
- **Analytics:** Organizers view reports based on attendance records and evaluation data.

### 5. Document Vault & Media
- **Media Paths:** `letter_image`, `permit_image`, and `equipment_image` are stored in `media/event_documents/`.
- **Templates:** Official `.docx` templates for approvals are stored in `static/templates/`.

### 6. Organization Mapping
Acronyms (e.g., `ITO`, `YEO`) are mapped to full names via the `ORG_FULL_NAMES` dictionary in `views.py`. Always use this mapping for UI consistency.

### 7. Student Verification
New student registrations are "Unverified" by default. They **MUST** be verified by an **Organizer** from their respective organization before they can log in.

---

## Directory Structure Highlights
- `campus_app/models.py`: Defines `OrgProfile`, `Event`, `Student`, and `Attendance`.
- `campus_app/views.py`: Core logic, security guards, and email triggers.
- `static/`: Assets separated by role (e.g., `static/css/student.css`, `static/js/admin.js`).
- `templates/`: HTML structure mirroring roles (e.g., `templates/organizer/`).
- `media/`: User-uploaded content (thumbnails, profiles, event docs).
