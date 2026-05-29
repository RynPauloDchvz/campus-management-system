import codecs

file_path = r'campus_app/models.py'

with codecs.open(file_path, 'r', 'utf-8') as f:
    content = f.read()

target = """    # 🟢 MGA UPLOADS SA DOCUMENT VAULT (LETTER, PERMIT, AT EQUIPMENT IMAGE)
    letter_image = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    permit_image = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    equipment_image = models.ImageField(upload_to='event_documents/', null=True, blank=True) 
    other_attachments = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    requirement_mode = models.IntegerField(null=True, blank=True, choices=[(2, '2 Documents'), (4, '4 Documents')])"""

replacement = """    # 🟢 MGA UPLOADS SA DOCUMENT VAULT (LETTER, PERMIT, AT EQUIPMENT IMAGE)
    letter_image = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    permit_image = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    equipment_image = models.ImageField(upload_to='event_documents/', null=True, blank=True) 
    other_attachments = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    
    # 🟢 4-File System Fields
    letter_of_approval = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    permit_to_conduct = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    excuse_letter_equipment = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    event_cover_photo = models.ImageField(upload_to='event_documents/', null=True, blank=True)

    # 🟢 2-File System Fields (Reschedule)
    letter_of_reschedule = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    reschedule_cover_photo = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    
    # Keep legacy fields for backward compatibility during migration if needed
    cover_photo = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    reschedule_cover_photo_legacy = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    
    requirement_mode = models.IntegerField(null=True, blank=True, choices=[(2, '2 Documents'), (4, '4 Documents')])"""

if target in content:
    with codecs.open(file_path, 'w', 'utf-8') as f:
        f.write(content.replace(target, replacement))
    print("Replaced successfully")
else:
    # try replacing without exact whitespace by searching for start and end
    idx_start = content.find("    # 🟢 MGA UPLOADS SA DOCUMENT VAULT")
    idx_end = content.find("    # Geofencing")
    if idx_start != -1 and idx_end != -1:
        with codecs.open(file_path, 'w', 'utf-8') as f:
            f.write(content[:idx_start] + replacement + "\n\n" + content[idx_end:])
        print("Replaced using indices")
    else:
        print("Could not find targets")
