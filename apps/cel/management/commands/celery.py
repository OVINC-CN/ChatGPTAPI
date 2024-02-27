import sys

from django.core.management import BaseCommand

from apps.cel import app


class Command(BaseCommand):
    """
    Celery Command
    """

    def handle(self, *args, **options):
        argv = sys.argv[2:]
        app.start(argv)

    def add_arguments(self, parser):
        parser.add_argument("worker", nargs="*")
        parser.add_argument("beat", nargs="*")
        parser.add_argument("-l")
        parser.add_argument("-f")
        parser.add_argument("-c")
