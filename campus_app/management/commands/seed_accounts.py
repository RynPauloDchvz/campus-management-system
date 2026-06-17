from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from campus_app.models import OrgProfile

class Command(BaseCommand):
    help = 'Seeds the database with the 11 Organizer and 11 Adviser accounts.'

    def handle(self, *args, **kwargs):
        organizations = ['ITO', 'CAO', 'FTO', 'ITS', 'YEO', 'PAS', 'ROTC', 'PRIDE', 'PUSO', 'SSC', 'NEWS']
        default_password = 'pupunicams'

        for org in organizations:
            # 1. CREATE ADVISER ACCOUNT
            adviser_username = f"{org.lower()}_adviser"
            if not User.objects.filter(username=adviser_username).exists():
                adviser = User.objects.create_user(
                    username=adviser_username,
                    email=f"{adviser_username}@gmail.com",
                    password=default_password
                )
                adviser.is_staff = True  # This flags them as an Adviser
                adviser.is_superuser = False
                adviser.save()
                self.stdout.write(self.style.SUCCESS(f"Created Adviser: {adviser_username}"))
            else:
                self.stdout.write(self.style.WARNING(f"Adviser {adviser_username} already exists."))

            # 2. CREATE ORGANIZER ACCOUNT
            organizer_username = f"{org.lower()}_organizer"
            if not User.objects.filter(username=organizer_username).exists():
                organizer = User.objects.create_user(
                    username=organizer_username,
                    email=f"{organizer_username}@gmail.com",
                    password=default_password
                )
                organizer.is_staff = False
                organizer.is_superuser = False
                organizer.save()
                
                # Link to OrgProfile
                OrgProfile.objects.create(
                    user=organizer,
                    organization=org
                )
                self.stdout.write(self.style.SUCCESS(f"Created Organizer: {organizer_username} with OrgProfile {org}"))
            else:
                self.stdout.write(self.style.WARNING(f"Organizer {organizer_username} already exists."))

        self.stdout.write(self.style.SUCCESS("Successfully seeded all 11 Adviser and Organizer accounts!"))
