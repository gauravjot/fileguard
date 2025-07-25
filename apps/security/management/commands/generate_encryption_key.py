from Crypto.Random import get_random_bytes
from django.core.management.base import BaseCommand, CommandParser
from core.settings import BASE_DIR


KEY_PATH = BASE_DIR / 'config' / 'encryption_key.key'


class Command(BaseCommand):
    help = 'Generate encryption keys for project.'

    def add_arguments(self, parser: CommandParser) -> None:
        # Check --force argument
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force generation of encryption key even if it already exists.'
        )

    def handle(self, *args, **kwargs):
        # Check if the key file already exists
        if KEY_PATH.exists() and not kwargs['force']:
            self.stdout.write("Encryption key file already exists.")
            return
        with open(KEY_PATH, 'wb') as f:
            f.write(get_random_bytes(32))
        self.stdout.write("Key generated successfully.")
