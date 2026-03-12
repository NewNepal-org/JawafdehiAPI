# -*- coding: utf-8 -*-
"""
Management command to seed rich development/inspection data.

Creates a variety of entities, cases (across all states), document sources,
and CaseEntityRelationship entries covering all relationship types so you can
inspect the admin UI, REST API, and entity endpoint locally.

Usage:
    poetry run python manage.py seed_dev_data
    poetry run python manage.py seed_dev_data --clear
    poetry run python manage.py seed_dev_data --clear --no-confirm
"""

from django.core.management.base import BaseCommand
from django.db import connection

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

ENTITIES = [
    # (nes_id, display_name)
    ("entity:person/kp-sharma-oli", "KP Sharma Oli"),
    ("entity:person/pushpa-kamal-dahal", "Pushpa Kamal Dahal"),
    ("entity:person/sher-bahadur-deuba", "Sher Bahadur Deuba"),
    ("entity:person/ram-chandra-paudel", "Ram Chandra Paudel"),
    ("entity:person/bishnu-prasad-paudel", "Bishnu Prasad Paudel"),
    ("entity:person/janardan-sharma", "Janardan Sharma"),
    ("entity:person/top-bahadur-rayamajhi", "Top Bahadur Rayamajhi"),
    ("entity:person/dilendra-prasad-badu", "Dilendra Prasad Badu"),
    ("entity:person/rabi-lamichhane", "Rabi Lamichhane"),
    ("entity:person/prem-bahadur-singh", "Prem Bahadur Singh"),
    ("entity:organization/nea", "Nepal Electricity Authority"),
    ("entity:organization/nepal-airlines", "Nepal Airlines Corporation"),
    ("entity:organization/ciaa", "CIAA"),
    ("entity:organization/nrb", "Nepal Rastra Bank"),
    (
        "entity:organization/civil-aviation-authority",
        "Civil Aviation Authority of Nepal",
    ),
    (
        "entity:organization/dept-revenue-investigation",
        "Department of Revenue Investigation",
    ),
    ("entity:location/kathmandu", "Kathmandu"),
    ("entity:location/lalita-niwas", "Lalita Niwas, Baluwatar"),
    ("entity:location/bansbari-plot", "Bansbari Land Plot"),
]

SOURCES = [
    {
        "source_id": "source:2020:ciaa-lalita-niwas",
        "title": "CIAA Investigation Report - Lalita Niwas Land Grab",
        "description": "CIAA report documenting forged land certificates and illegal transfers.",
        "source_type": "LEGAL_COURT_ORDER",
        "url": ["https://example.com/ciaa-lalita-niwas-2020"],
    },
    {
        "source_id": "source:2019:auditor-general-nea",
        "title": "Auditor General Report - NEA Procurement Irregularities",
        "description": "Annual audit findings highlighting irregular procurement in NEA transformer purchases.",
        "source_type": "OFFICIAL_GOVERNMENT",
        "url": ["https://example.com/ag-nea-2019"],
    },
    {
        "source_id": "source:2021:airlines-widebody",
        "title": "Investigative Report - Widebody Aircraft Purchase",
        "description": "Investigative piece detailing alleged kickbacks in Nepal Airlines widebody procurement.",
        "source_type": "INVESTIGATIVE_REPORT",
        "url": ["https://example.com/airlines-widebody-2021"],
    },
    {
        "source_id": "source:2022:revenue-leak",
        "title": "DRI Report - Revenue Leakage via Under-invoicing",
        "description": "DRI report on systematic under-invoicing at customs.",
        "source_type": "FINANCIAL_FORENSIC",
        "url": ["https://example.com/dri-revenue-2022"],
    },
    {
        "source_id": "source:2023:minister-speech",
        "title": "Video - Minister Speech on Infrastructure Budget",
        "description": "Recorded speech where minister makes infrastructure budget promises.",
        "source_type": "SOCIAL_MEDIA",
        "url": ["https://example.com/minister-speech-2023"],
    },
]

# Each entity entry: (nes_id, relationship_type, notes_or_None)
CASES = [
    # ------------------------------------------------------------------
    # 1. PUBLISHED - corruption, alleged + related + witness
    # ------------------------------------------------------------------
    {
        "case_id": "lalita-niwas-land-grab",
        "version": 1,
        "case_type": "CORRUPTION",
        "state": "PUBLISHED",
        "title": "Lalita Niwas Land Grab",
        "short_description": "Senior officials illegally transferred state-owned Lalita Niwas land using forged documents.",
        "tags": ["land-grab", "corruption", "forged-documents", "public-property"],
        "description": "<p>Senior politicians were implicated in the illegal transfer of state-owned Lalita Niwas property in Baluwatar, Kathmandu.</p>",
        "key_allegations": [
            "Forged land ownership certificates to transfer state property",
            "Collusion between politicians and land registry officials",
            "Illegal subdivision of state land into private plots",
        ],
        "case_start_date": "2012-01-01",
        "case_end_date": "2020-06-30",
        "entities": [
            (
                "entity:person/kp-sharma-oli",
                "alleged",
                "Prime Minister during key period",
            ),
            ("entity:person/pushpa-kamal-dahal", "alleged", None),
            ("entity:person/sher-bahadur-deuba", "alleged", None),
            ("entity:organization/ciaa", "related", "Investigating body"),
            (
                "entity:person/top-bahadur-rayamajhi",
                "witness",
                "Provided testimony on land records",
            ),
            ("entity:location/lalita-niwas", "related", None),
            ("entity:location/kathmandu", "related", None),
        ],
        "locations": ["entity:location/lalita-niwas"],
        "sources": ["source:2020:ciaa-lalita-niwas"],
        "versionInfo": {
            "version_number": 1,
            "change_summary": "Initial published version",
            "datetime": "2024-03-01T10:00:00Z",
        },
    },
    # ------------------------------------------------------------------
    # 2. PUBLISHED - corruption, NEA procurement
    # ------------------------------------------------------------------
    {
        "case_id": "nea-transformer-procurement",
        "version": 1,
        "case_type": "CORRUPTION",
        "state": "PUBLISHED",
        "title": "NEA Transformer Procurement Fraud",
        "short_description": "NEA officials manipulated procurement tenders causing NPR 2.4 billion in losses.",
        "tags": ["procurement", "nea", "corruption", "public-utilities"],
        "description": "<p>Officials split tenders to avoid open competition and directed contracts to favoured suppliers at 40% above market rate.</p>",
        "key_allegations": [
            "Artificial splitting of tenders to avoid open bidding",
            "Contracts awarded at 40% above market rate",
            "Kickbacks to procurement committee members",
        ],
        "case_start_date": "2016-07-01",
        "case_end_date": "2019-06-30",
        "entities": [
            (
                "entity:organization/nea",
                "alleged",
                "Procurement decisions made by NEA board",
            ),
            ("entity:person/dilendra-prasad-badu", "alleged", "Then CEO of NEA"),
            (
                "entity:person/bishnu-prasad-paudel",
                "related",
                "Minister overseeing energy sector",
            ),
            (
                "entity:person/janardan-sharma",
                "opposition",
                "Publicly demanded investigation",
            ),
            ("entity:organization/dept-revenue-investigation", "related", None),
        ],
        "locations": ["entity:location/kathmandu"],
        "sources": ["source:2019:auditor-general-nea"],
        "versionInfo": {
            "version_number": 1,
            "change_summary": "Initial published version",
            "datetime": "2024-04-15T09:00:00Z",
        },
    },
    # ------------------------------------------------------------------
    # 3. PUBLISHED - corruption, Nepal Airlines, includes victim type
    # ------------------------------------------------------------------
    {
        "case_id": "nepal-airlines-widebody",
        "version": 1,
        "case_type": "CORRUPTION",
        "state": "PUBLISHED",
        "title": "Nepal Airlines Widebody Aircraft Procurement Scandal",
        "short_description": "Alleged USD 5 million kickbacks in the purchase of two widebody aircraft.",
        "tags": ["airlines", "procurement", "kickbacks", "aviation"],
        "description": "<p>The A330 widebody purchase was marred by allegations of USD 5 million in kickbacks paid to Nepali officials.</p>",
        "key_allegations": [
            "USD 5 million kickbacks paid to facilitating officials",
            "Aircraft purchased at inflated prices without competitive bidding",
            "Civil Aviation approvals obtained without technical review",
        ],
        "case_start_date": "2018-01-01",
        "case_end_date": "2021-12-31",
        "entities": [
            ("entity:organization/nepal-airlines", "alleged", "Procurement authority"),
            ("entity:person/prem-bahadur-singh", "alleged", "Then Tourism Minister"),
            (
                "entity:organization/civil-aviation-authority",
                "related",
                "Provided regulatory approvals",
            ),
            (
                "entity:person/rabi-lamichhane",
                "opposition",
                "Led parliamentary inquiry",
            ),
            (
                "entity:person/pushpa-kamal-dahal",
                "victim",
                "Government credibility affected",
            ),
        ],
        "locations": ["entity:location/kathmandu"],
        "sources": ["source:2021:airlines-widebody"],
        "versionInfo": {
            "version_number": 1,
            "change_summary": "Initial published version",
            "datetime": "2024-05-20T11:00:00Z",
        },
    },
    # ------------------------------------------------------------------
    # 4. PUBLISHED - broken promises
    # ------------------------------------------------------------------
    {
        "case_id": "fast-track-highway-promise",
        "version": 1,
        "case_type": "PROMISES",
        "state": "PUBLISHED",
        "title": "Kathmandu-Tarai Fast Track Highway Deadline Failures",
        "short_description": "Multiple governments promised highway completion by 2024; project remains under 30% complete.",
        "tags": ["infrastructure", "highway", "broken-promise", "fast-track"],
        "description": "<p>The Fast Track Highway was promised complete by multiple PMs. Only 30% construction is done as of 2026.</p>",
        "key_allegations": [
            "Promised completion by 2020 - missed by years",
            "NPR 45 billion disbursed with minimal visible progress",
            "Repeated budget diversions from project fund",
        ],
        "case_start_date": "2017-01-01",
        "entities": [
            (
                "entity:person/kp-sharma-oli",
                "alleged",
                "Made 2020 completion promise as PM",
            ),
            (
                "entity:person/pushpa-kamal-dahal",
                "alleged",
                "Made 2022 completion promise as PM",
            ),
            (
                "entity:person/sher-bahadur-deuba",
                "alleged",
                "Made 2023 completion promise as PM",
            ),
            (
                "entity:person/ram-chandra-paudel",
                "related",
                "President overseeing national projects",
            ),
        ],
        "locations": ["entity:location/kathmandu"],
        "sources": ["source:2023:minister-speech"],
        "versionInfo": {
            "version_number": 1,
            "change_summary": "Initial published version",
            "datetime": "2024-06-01T08:00:00Z",
        },
    },
    # ------------------------------------------------------------------
    # 5. IN_REVIEW - visible only with EXPOSE_CASES_IN_REVIEW=True
    # ------------------------------------------------------------------
    {
        "case_id": "customs-revenue-leak",
        "version": 1,
        "case_type": "CORRUPTION",
        "state": "IN_REVIEW",
        "title": "Customs Under-invoicing Revenue Leak",
        "short_description": "Systematic under-invoicing at TIA customs allegedly costing NPR 8 billion annually.",
        "tags": ["customs", "revenue", "under-invoicing", "corruption"],
        "description": "<p>DRI investigations uncovered a network colluding to under-invoice goods and reduce import duties.</p>",
        "key_allegations": [
            "Goods declared at 10-20% of actual value",
            "Cash bribes paid to customs officials per container",
            "NRB forex records show matching discrepancies",
        ],
        "case_start_date": "2010-01-01",
        "entities": [
            (
                "entity:organization/dept-revenue-investigation",
                "related",
                "Investigating body",
            ),
            ("entity:organization/nrb", "related", "Financial intelligence unit"),
            (
                "entity:person/bishnu-prasad-paudel",
                "alleged",
                "Finance Minister during peak period",
            ),
            ("entity:person/janardan-sharma", "alleged", "Then Finance Minister"),
        ],
        "locations": ["entity:location/kathmandu"],
        "sources": ["source:2022:revenue-leak"],
        "versionInfo": {
            "version_number": 1,
            "change_summary": "Pending moderator review",
            "datetime": "2025-01-10T14:00:00Z",
        },
    },
    # ------------------------------------------------------------------
    # 6. DRAFT - not visible in public API
    # ------------------------------------------------------------------
    {
        "case_id": "bansbari-land-draft",
        "version": 1,
        "case_type": "CORRUPTION",
        "state": "DRAFT",
        "title": "Bansbari Land Allocation Irregularities [DRAFT]",
        "short_description": "Under investigation: alleged irregular allocation of government land in Bansbari.",
        "tags": ["land", "draft", "bansbari"],
        "description": "<p>Draft case - not yet ready for review.</p>",
        "key_allegations": ["Land allocated without competitive process"],
        "entities": [
            ("entity:person/ram-chandra-paudel", "alleged", None),
            ("entity:location/bansbari-plot", "related", None),
        ],
        "locations": ["entity:location/bansbari-plot"],
        "sources": [],
        "versionInfo": {},
    },
    # ------------------------------------------------------------------
    # 7. CLOSED - archived, not visible in public API
    # ------------------------------------------------------------------
    {
        "case_id": "yeti-airlines-crash-inquiry",
        "version": 1,
        "case_type": "CORRUPTION",
        "state": "CLOSED",
        "title": "Yeti Airlines Crash - Regulatory Oversight Failure [CLOSED]",
        "short_description": "Closed inquiry into CAAN failures related to the 2023 Pokhara crash.",
        "tags": ["aviation", "closed", "safety"],
        "description": "<p>Closed - findings handed to relevant authorities.</p>",
        "key_allegations": ["CAAN failed to enforce mandatory safety audits"],
        "entities": [
            (
                "entity:organization/civil-aviation-authority",
                "alleged",
                "Regulatory failures identified",
            ),
            ("entity:person/prem-bahadur-singh", "related", "Then Tourism Minister"),
        ],
        "locations": ["entity:location/kathmandu"],
        "sources": [],
        "versionInfo": {
            "version_number": 1,
            "change_summary": "Closed after findings transferred",
            "datetime": "2024-01-01T00:00:00Z",
        },
    },
]


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Seed rich development data: entities, cases, sources, and relationships"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing Cases, Sources, and Entities before seeding",
        )
        parser.add_argument(
            "--no-confirm",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        from cases.models import (
            Case,
            CaseEntityRelationship,
            CaseState,
            DocumentSource,
            JawafEntity,
        )

        db = connection.settings_dict
        self.stdout.write(self.style.WARNING("\nDatabase: " + db["NAME"]))

        if options["clear"]:
            self.stdout.write(
                self.style.WARNING(
                    "  --clear flag set: will DELETE existing Cases, Sources, Entities."
                )
            )

        if not options["no_confirm"]:
            confirm = input('\nType "yes" to continue: ')
            if confirm.strip().lower() != "yes":
                self.stdout.write(self.style.ERROR("Aborted."))
                return

        # ----------------------------------------------------------------
        # Optionally wipe
        # ----------------------------------------------------------------
        if options["clear"]:
            nc = Case.objects.count()
            ns = DocumentSource.objects.count()
            ne = JawafEntity.objects.count()
            Case.objects.all().delete()
            DocumentSource.objects.all().delete()
            JawafEntity.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(
                    "  Cleared %d cases, %d sources, %d entities." % (nc, ns, ne)
                )
            )

        # ----------------------------------------------------------------
        # 1. Entities
        # ----------------------------------------------------------------
        self.stdout.write("\n[1/3] Creating entities...")
        entity_map = {}
        for nes_id, display_name in ENTITIES:
            entity, created = JawafEntity.objects.get_or_create(
                nes_id=nes_id,
                defaults={"display_name": display_name},
            )
            entity_map[nes_id] = entity
            self.stdout.write(
                "  [%s] %s" % ("created" if created else "exists ", nes_id)
            )

        # ----------------------------------------------------------------
        # 2. Document sources
        # ----------------------------------------------------------------
        self.stdout.write("\n[2/3] Creating document sources...")
        source_map = {}
        for s in SOURCES:
            source, created = DocumentSource.objects.get_or_create(
                source_id=s["source_id"],
                defaults={
                    "title": s["title"],
                    "description": s["description"],
                    "source_type": s["source_type"],
                    "url": s["url"],
                },
            )
            source_map[s["source_id"]] = source
            self.stdout.write(
                "  [%s] %s" % ("created" if created else "exists ", s["source_id"])
            )

        # ----------------------------------------------------------------
        # 3. Cases + relationships
        # ----------------------------------------------------------------
        self.stdout.write("\n[3/3] Creating cases and relationships...")
        for cd in CASES:
            case, created = Case.objects.get_or_create(
                case_id=cd["case_id"],
                version=cd["version"],
                defaults={
                    "case_type": cd["case_type"],
                    "state": cd["state"],
                    "title": cd["title"],
                    "short_description": cd.get("short_description", ""),
                    "description": cd.get("description", ""),
                    "tags": cd.get("tags", []),
                    "key_allegations": cd.get("key_allegations", []),
                    "case_start_date": cd.get("case_start_date"),
                    "case_end_date": cd.get("case_end_date"),
                    "versionInfo": cd.get("versionInfo", {}),
                },
            )
            self.stdout.write(
                "\n  [%s] %s  (%s)"
                % ("created" if created else "exists ", cd["case_id"], cd["state"])
            )

            for nes_id, rel_type, notes in cd.get("entities", []):
                entity = entity_map.get(nes_id)
                if not entity:
                    self.stdout.write(self.style.WARNING("    ! not found: " + nes_id))
                    continue
                _, rel_created = CaseEntityRelationship.objects.get_or_create(
                    case=case,
                    entity=entity,
                    type=rel_type,
                    defaults={"notes": notes},
                )
                note_str = ("  -> " + notes) if notes else ""
                self.stdout.write(
                    "    %s [%-10s] %s%s"
                    % (
                        "+" if rel_created else "=",
                        rel_type,
                        entity.display_name,
                        note_str,
                    )
                )

            for loc_nes_id in cd.get("locations", []):
                loc = entity_map.get(loc_nes_id)
                if loc:
                    case.locations.add(loc)

            evidence = [
                {"source_id": sid, "description": ""}
                for sid in cd.get("sources", [])
                if sid in source_map
            ]
            if evidence:
                case.evidence = evidence
                case.save(update_fields=["evidence"])

        # ----------------------------------------------------------------
        # Summary
        # ----------------------------------------------------------------
        self.stdout.write("\n" + "-" * 56)
        self.stdout.write(self.style.SUCCESS("Seed complete!\n"))
        for state in [
            CaseState.PUBLISHED,
            CaseState.IN_REVIEW,
            CaseState.DRAFT,
            CaseState.CLOSED,
        ]:
            n = Case.objects.filter(state=state).count()
            self.stdout.write("  %-12s  %d case(s)" % (state, n))
        self.stdout.write("")
        self.stdout.write("  Entities  : %d" % JawafEntity.objects.count())
        self.stdout.write("  Sources   : %d" % DocumentSource.objects.count())
        self.stdout.write("  Rel rows  : %d" % CaseEntityRelationship.objects.count())
        self.stdout.write(self.style.SUCCESS("\nEndpoints to try:"))
        self.stdout.write("  http://127.0.0.1:8000/api/cases/")
        self.stdout.write("  http://127.0.0.1:8000/api/entities/")
        self.stdout.write("  http://127.0.0.1:8000/api/cases/lalita-niwas-land-grab/")
        self.stdout.write(
            "  http://127.0.0.1:8000/api/cases/nea-transformer-procurement/"
        )
        self.stdout.write(
            "  http://127.0.0.1:8000/api/cases/fast-track-highway-promise/"
        )
        self.stdout.write("  http://127.0.0.1:8000/admin/")
