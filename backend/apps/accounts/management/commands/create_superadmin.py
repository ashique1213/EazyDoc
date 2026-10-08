from django.core.management.base import BaseCommand, CommandError
from apps.accounts.models import User, UserRole, UserStatus


class Command(BaseCommand):
    help = "Creates or updates a SUPER_ADMIN user securely via CLI."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, type=str, help="Super admin email address")
        parser.add_argument("--password", required=True, type=str, help="Super admin password")
        parser.add_argument("--first-name", default="Super", type=str, help="First name")
        parser.add_argument("--last-name", default="Admin", type=str, help="Last name")
        parser.add_argument("--phone", default=None, type=str, help="Optional contact phone")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        password = options["password"]
        first_name = options["first_name"]
        last_name = options["last_name"]
        phone = options["phone"]

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "role": UserRole.SUPER_ADMIN,
                "status": UserStatus.ACTIVE,
                "is_staff": True,
                "is_superuser": True,
                "is_verified": True,
            },
        )

        user.set_password(password)
        user.role = UserRole.SUPER_ADMIN
        user.status = UserStatus.ACTIVE
        user.is_staff = True
        user.is_superuser = True
        user.is_verified = True
        user.is_active = True
        if phone:
            user.phone = phone
        user.save()

        action = "Created" if created else "Updated existing user to"
        self.stdout.write(
            self.style.SUCCESS(f"Successfully {action} SUPER_ADMIN: {user.email}")
        )
