from django.core.management.base import BaseCommand, CommandError

from resume_api.services.rag_indexer import reindex_rag


class Command(BaseCommand):
    help = "Rebuild the local ChromaDB RAG index from the Turtle resume graph."

    def add_arguments(self, parser):
        parser.add_argument("--rdf-file", help="Optional path to a Turtle file.")

    def handle(self, *args, **options):
        try:
            count = reindex_rag(options.get("rdf_file"))
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Indexed {count} resume chunks."))