"""
Management command to scrape case information using Google AI.

Usage: python manage.py scrape_case <source_path> [<source_path> ...] [options]
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from django.core.management.base import BaseCommand, CommandError
from google import genai
from google.genai.types import GenerateContentConfig, GoogleSearch, HttpOptions, Tool
from google.oauth2 import service_account
from pydantic import BaseModel, Field
from datetime import date


class DocumentSource(BaseModel):
    """Documents, sources, and evidences."""
    title: str = Field(description="Source title")
    url: str = Field(description="URL to the source")
    description: str = Field(default="", description="Brief description of the source")


class Location(BaseModel):
    other: str | None = Field(default=None, description="Other location details")
    ward_no: int | None = Field(default=None, description="Ward number")
    municipality: str | None = Field(default=None, description="Municipality name")
    district: str | None = Field(default=None, description="District name")
    province: str | None = Field(default=None, description="Province name")


class TimelineEntry(BaseModel):
    event_date: date = Field(description="Date of the event")
    title: str = Field(description="Title of the event")
    description: str = Field(description="Description of what happened")


class Case(BaseModel):
    title: str = Field(description="Case title")
    description: str = Field(description="Detailed description of the case in rich HTML format with proper formatting, paragraphs, lists, and emphasis")
    unverified_info: str = Field(default="", description="Unverified or incomplete information in rich HTML format")
    key_allegations: list[str] = Field(description="List of key allegations")
    alleged_entities: list[str] = Field(description="Names of entities being accused")
    related_entities: list[str] = Field(default_factory=list, description="Names of related entities")
    locations: list[Location] = Field(default_factory=list, description="Locations related to the case")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    case_start_date: date | None = Field(default=None, description="When the incident began")
    case_end_date: date | None = Field(default=None, description="When the incident ended")
    timeline: list[TimelineEntry] = Field(default_factory=list, description="Timeline of events")
    sources: list[DocumentSource] = Field(description="Document sources supporting the case")


SYSTEM_PROMPT_TEMPLATE = """You are a research assistant for a world-class corruption and accountability database focused on Nepali public entities.

LANGUAGE: {language_instruction}

FORMATTING: The description and unverified_info fields must be in rich HTML format:
- Use <p> tags for paragraphs
- Use <strong> for emphasis on important points
- Use <ul> and <li> for bullet lists
- Use <ol> and <li> for numbered lists
- Use <a href="..."> for links to sources
- Use proper HTML structure for readability

ACCURACY IS CRITICAL. Every piece of information must be:
- Factually correct and verifiable
- Backed by credible sources with URLs whenever possible
- Cross-referenced when possible

For sources:
- ALWAYS provide URLs/links whenever available
- Prioritize first-hand evidence (court documents, official reports, government records) over news reporting
- Secondary priority: reputable news outlets
- Include the exact URL where information was found
- If no URL is available, clearly state the source type (e.g., "Internal document", "Interview", etc.)
- Provide clear descriptions of what each source contains

For structured fields (dates, names, amounts, timeline, evidence):
- Only include information that is precise and verifiable
- All dates must be exact (YYYY-MM-DD format)
- All names must be complete and accurate
- All amounts must be specific

For uncertain or incomplete information:
- Place it in the unverified_info field
- Include approximate dates, partial names, estimated amounts, or unconfirmed details here
- This allows us to track leads while maintaining data integrity in primary fields

This database will be used for public accountability.
"""

PHASE1_PROMPT = """Research assistant: Extract ALL information about this case from available sources.

Include:
- Facts, allegations, and claims
- Names, dates, amounts, locations
- Timeline of events
- Quotes and specific details
- Source URLs

Provide comprehensive raw findings."""

PHASE2_PROMPT = """Structure the research into a verified accountability case.

RULES:
- Only verified, precise information in structured fields
- Exact dates (YYYY-MM-DD), complete names, specific amounts
- Uncertain/incomplete information → unverified_info field
- All sources must have URLs and descriptions
- Format description and unverified_info as rich HTML with proper tags (<p>, <strong>, <ul>, <li>, <a>, etc.)

Maintain data integrity for public accountability."""


class Command(BaseCommand):
    help = 'Scrape case information from source files using Google AI'

    def add_arguments(self, parser):
        parser.add_argument(
            'source_paths',
            nargs='+',
            type=str,
            help='One or more source file paths to scrape'
        )
        parser.add_argument(
            '--language',
            type=str,
            default='en',
            choices=['en', 'np'],
            help='Output language: en (English) or np (Nepali). Default: en'
        )
        parser.add_argument(
            '--work-dir',
            type=str,
            default='/tmp',
            help='Base directory for work files (default: /tmp)'
        )
        parser.add_argument(
            '--service-account',
            type=str,
            default='.service-account-key.json',
            help='Path to Google service account key file (default: .service-account-key.json)'
        )
        parser.add_argument(
            '--project',
            type=str,
            help='Google Cloud project ID (defaults to project_id from service account key)'
        )
        parser.add_argument(
            '--location',
            type=str,
            default='us-central1',
            help='Google Cloud location'
        )
        parser.add_argument(
            '--model',
            type=str,
            default='gemini-2.5-pro',
            help='Google AI model to use'
        )

    def handle(self, *args, **options):
        """Execute the scrape command."""
        start_time = datetime.now()
        
        source_paths = options['source_paths']
        language = options['language']
        work_dir_base = options['work_dir']
        service_account_path = options['service_account']
        project = options['project']
        location = options['location']
        model = options['model']
        
        # Set language instruction based on selected language
        if language == 'np':
            language_instruction = "Provide all responses in Nepali language (नेपाली भाषामा जवाफ दिनुहोस्)."
        else:
            language_instruction = "Provide all responses in English language."
        
        # Generate system prompt with language instruction
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(language_instruction=language_instruction)

        # Validate source paths
        self.log_error("Validating source paths...")
        for path_str in source_paths:
            path = Path(path_str)
            if not path.exists():
                raise CommandError(f"Source path does not exist: {path_str}")
            if not path.is_file():
                raise CommandError(f"Source path is not a file: {path_str}")

        # Validate service account
        service_account_file = Path(service_account_path)
        if not service_account_file.exists():
            raise CommandError(f"Service account key file not found: {service_account_path}")

        # Create work directory
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        work_dir = Path(work_dir_base) / f"scrape-case-{timestamp}"
        work_dir.mkdir(parents=True, exist_ok=True)
        
        # Output work directory to stdout
        print(str(work_dir))

        self.log_error(f"Created work directory: {work_dir}")

        # Initialize Google AI client
        self.log_error("Initializing Google AI client...")
        credentials = service_account.Credentials.from_service_account_file(
            str(service_account_file),
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        # Read project_id from service account if not provided
        if not project:
            with open(service_account_file, 'r') as f:
                service_account_info = json.load(f)
                project = service_account_info.get('project_id')
                if not project:
                    raise CommandError("project_id not found in service account key file")
                self.log_error(f"Using project_id from service account: {project}")
        
        client = genai.Client(
            http_options=HttpOptions(api_version="v1"),
            vertexai=True,
            credentials=credentials,
            project=project,
            location=location
        )

        # Read source files
        self.log_error("Reading source files...")
        source_contents = []
        for path_str in source_paths:
            path = Path(path_str)
            try:
                content = path.read_text(encoding='utf-8')
                source_contents.append({
                    'path': path_str,
                    'content': content
                })
                self.log_error(f"  Read {len(content)} characters from {path_str}")
            except Exception as e:
                raise CommandError(f"Failed to read {path_str}: {e}")

        # Phase 1: Extract raw information from all sources combined
        self.log_error("\nPhase 1: Extracting information...")
        
        # Concatenate all source contents
        combined_sources = "\n\n---SOURCE DOCUMENT---\n\n".join(
            [f"File: {s['path']}\n\n{s['content']}" for s in source_contents]
        )
        
        query = f"Extract all relevant information from these documents:\n\n{combined_sources}"
        
        response = client.models.generate_content(
            model=model,
            contents=f"{PHASE1_PROMPT}\n\n{query}",
            config=GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[Tool(google_search=GoogleSearch())]
            ),
        )
        
        raw_data = response.text
        
        # Save to intermediate file
        phase1_file = work_dir / "phase1-raw.md"
        phase1_file.write_text(raw_data, encoding='utf-8')
        self.log_error(f"  Saved {len(raw_data)} characters to {phase1_file.name}")

        # Phase 2: Structure the data
        self.log_error("\nPhase 2: Structuring data...")
        
        prompt = f"{PHASE2_PROMPT}\n\nRaw Research:\n{raw_data}"
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=Case,
                system_instruction=system_prompt
            ),
        )

        # Parse and validate the case
        case = Case.model_validate_json(response.text)
        
        # Save final result
        result_file = work_dir / "case-result.json"
        result_file.write_text(case.model_dump_json(indent=2), encoding='utf-8')
        
        # Calculate elapsed time
        end_time = datetime.now()
        elapsed = end_time - start_time
        elapsed_seconds = elapsed.total_seconds()
        
        self.log_error(f"\nCompleted successfully!")
        self.log_error(f"  Case title: {case.title}")
        self.log_error(f"  Allegations: {len(case.key_allegations)}")
        self.log_error(f"  Timeline entries: {len(case.timeline)}")
        self.log_error(f"  Sources: {len(case.sources)}")
        self.log_error(f"  Result saved to: {result_file}")
        self.log_error(f"  Total time elapsed: {elapsed_seconds:.2f} seconds")

    def log_error(self, message):
        """Write log messages to stderr."""
        self.stderr.write(message)
