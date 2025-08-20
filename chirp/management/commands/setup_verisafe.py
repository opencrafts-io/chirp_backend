from django.core.management.base import BaseCommand
from django.conf import settings
from chirp.verisafe_client import get_verisafe_client
from chirp.user_search import get_user_search_service

class Command(BaseCommand):
    help = 'Setup and test Verisafe integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test connection to Verisafe',
        )
        parser.add_argument(
            '--test-search',
            action='store_true',
            help='Test user search functionality',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting Verisafe integration setup...')

        self.check_configuration()

        if options['test_connection']:
            self.test_connection()

        if options['test_search']:
            self.test_search()

    def check_configuration(self):
        """Check if Verisafe configuration is properly set"""
        self.stdout.write('Checking Verisafe configuration...')

        base_url = getattr(settings, 'VERISAFE_BASE_URL', None)
        service_token = getattr(settings, 'VERISAFE_SERVICE_TOKEN', None)

        if not base_url:
            self.stdout.write(
                'VERISAFE_BASE_URL not set in settings'
            )
        else:
            self.stdout.write(
                f'VERISAFE_BASE_URL: {base_url}'
            )

        if not service_token:
            self.stdout.write(
                'VERISAFE_SERVICE_TOKEN not set in settings'
            )
        else:
            self.stdout.write(
                'VERISAFE_SERVICE_TOKEN: [CONFIGURED]'
            )

    def test_connection(self):
        """Test connection to Verisafe"""
        self.stdout.write('Testing connection to Verisafe...')

        try:
            client = get_verisafe_client()

            response = client.search_users('test', limit=1)

            if response is not None:
                self.stdout.write(
                    '✓ Connection to Verisafe successful'
                )
            else:
                self.stdout.write(
                    '✗ Connection to Verisafe failed'
                )

        except Exception as e:
            self.stdout.write(
                f'✗ Connection test failed: {e}'
            )

    def test_search(self):
        """Test user search functionality"""
        self.stdout.write('Testing user search functionality...')

        try:
            search_service = get_user_search_service()

            results = search_service.search_users('test', limit=5)

            self.stdout.write(
                f'✓ User search test completed. Found {len(results)} results'
            )

            if results:
                self.stdout.write('Sample results:')
                for user in results[:3]:
                    self.stdout.write(f'  - {user.get("name", "Unknown")} ({user.get("email", "No email")})')

        except Exception as e:
            self.stdout.write(
                f'✗ User search test failed: {e}'
            )
