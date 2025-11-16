from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime


class Command(BaseCommand):
    help = 'Seed example allegations data'

    def handle(self, *args, **options):
        from allegations.models import Allegation, DocumentSource, Evidence, Timeline, Modification
        
        self.stdout.write(self.style.WARNING('WARNING: This will delete all existing allegations and document sources!'))
        confirm = input('Type "yes" to continue: ')
        
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.ERROR('Aborted.'))
            return
        
        Allegation.objects.all().delete()
        DocumentSource.objects.all().delete()
        
        self.stdout.write('Creating allegations...')
        
        # 1. Lalita Niwas
        lalita = Allegation.objects.create(
            allegation_type="corruption",
            state="current",
            title="Lalita Niwas Land Grab Scandal",
            alleged_entities=["balakrishna-khand", "madhav-prasad-ghimire"],
            related_entities=["nepal-government", "land-revenue-office-dillibazar"],
            location_id="kathmandu-district",
            description="""# Lalita Niwas Land Grab Case

## Overview
The Lalita Niwas land grab case involves the illegal transfer of approximately 175 ropanis of government land in Baluwatar, Kathmandu. The land, originally part of the Lalita Niwas palace complex, was fraudulently registered in the names of various individuals through forged documents.

## Key Details
- **Land Area**: 175 ropanis (approximately 8.9 hectares)
- **Location**: Baluwatar, Kathmandu
- **Estimated Value**: Over NPR 3 billion
- **Method**: Forged documents and illegal land registration

## Allegations
Multiple government officials, including former ministers and land revenue officers, are accused of facilitating the illegal transfer through document forgery and abuse of authority.""",
            key_allegations="Illegal transfer of 175 ropanis of government land through forged documents; involvement of high-ranking officials; estimated loss of NPR 3+ billion to state",
            status="under_investigation",
            created_at=timezone.make_aware(datetime(2018, 3, 10)),
            first_public_date=timezone.make_aware(datetime(2018, 3, 15)),
        )
        
        src1 = DocumentSource.objects.create(
            title="CIAA investigation report on Lalita Niwas",
            description="CIAA investigation report documenting forged land ownership certificates",
            url="https://ciaa.gov.np/reports/lalita-niwas",
            source_type="government",
        )
        src2 = DocumentSource.objects.create(
            title="Court documents from Lalita Niwas case",
            description="Supreme Court and District Court case files",
            source_type="government",
        )
        
        Evidence.objects.create(allegation=lalita, source=src1, description="CIAA investigation report documenting forged land ownership certificates", order=1)
        Evidence.objects.create(allegation=lalita, source=src2, description="Supreme Court and District Court case files", order=2)
        
        Timeline.objects.create(allegation=lalita, date=datetime(2018, 3, 15).date(), title="Case filed", description="CIAA files case against officials involved in land grab", order=1)
        Timeline.objects.create(allegation=lalita, date=datetime(2020, 7, 20).date(), title="Supreme Court ruling", description="Supreme Court orders investigation into all involved parties", order=2)
        
        Modification.objects.create(allegation=lalita, action="created", notes="Initial allegation created")
        
        # 2. Rabi Lamichhane
        rabi = Allegation.objects.create(
            allegation_type="corruption",
            state="current",
            title="Rabi Lamichhane Cooperative Fraud and Citizenship Controversy",
            alleged_entities=["rabi-lamichhane"],
            related_entities=["rastriya-swatantra-party", "gorkha-media-network"],
            location_id="chitwan-district",
            description="""# Rabi Lamichhane Controversies

## Overview
Rabi Lamichhane, president of Rastriya Swatantra Party and former Deputy Prime Minister, faces multiple allegations including cooperative fraud and citizenship irregularities.

## Cooperative Fraud Allegations
- Accused of embezzling funds from Suryadarshan Cooperative
- Alleged misuse of cooperative funds for personal media business
- Multiple cooperative victims filed complaints

## Citizenship Controversy
- Questions raised about validity of his Nepali citizenship
- Allegations of holding US citizenship while serving as minister
- Supreme Court ordered investigation into citizenship status

## Political Impact
The allegations led to his resignation as Deputy Prime Minister and Home Minister, and subsequent arrest in the cooperative fraud case.""",
            key_allegations="Embezzlement of cooperative funds; citizenship fraud; misuse of public office",
            status="under_investigation",
            created_at=timezone.make_aware(datetime(2023, 5, 20)),
            first_public_date=timezone.make_aware(datetime(2023, 5, 18)),
        )
        
        src3 = DocumentSource.objects.create(
            title="Cooperative fraud complaint documents",
            description="Police complaint filed by cooperative victims",
            source_type="government",
        )
        src4 = DocumentSource.objects.create(
            title="Cooperative victims' testimonies",
            description="Testimonies from cooperative fraud victims",
            source_type="crowdsourced",
        )
        
        Evidence.objects.create(allegation=rabi, source=src3, description="Police complaint filed by cooperative victims", order=1)
        Evidence.objects.create(allegation=rabi, source=src4, description="Cooperative victims' testimonies and financial records", order=2)
        
        Timeline.objects.create(allegation=rabi, date=datetime(2023, 11, 28).date(), title="Supreme Court orders citizenship investigation", description="Supreme Court directs authorities to investigate citizenship irregularities", order=1)
        Timeline.objects.create(allegation=rabi, date=datetime(2024, 1, 18).date(), title="Arrested in cooperative fraud case", description="Police arrest Lamichhane in connection with cooperative embezzlement", order=2)
        
        Modification.objects.create(allegation=rabi, action="created", notes="Initial allegation created")
        
        # 3. Melamchi
        melamchi = Allegation.objects.create(
            allegation_type="breach_of_trust",
            state="current",
            title="Melamchi Water Supply Project Delays and Cost Overruns",
            alleged_entities=["nepal-government", "melamchi-water-supply-board"],
            related_entities=["ministry-of-water-supply"],
            location_id="kathmandu-valley",
            description="""# Melamchi Water Supply Project Failure

## Overview
The Melamchi Water Supply Project, initiated in 1998 to solve Kathmandu Valley's water crisis, has faced decades of delays, massive cost overruns, and repeated failures.

## Timeline of Broken Trust
- **1998**: Project initiated with 5-year timeline
- **2016**: Finally inaugurated after 18 years
- **2021**: System damaged by floods
- **2024**: Still not fully operational

## Financial Impact
- Original budget: NPR 16 billion
- Current cost: Over NPR 100 billion
- Kathmandu residents still face severe water shortages

## Breach of Public Trust
Citizens were promised reliable water supply for over two decades, with multiple governments failing to deliver despite massive public investment.""",
            key_allegations="26+ years of delays; cost overrun from NPR 16B to NPR 100B+; failure to deliver promised water supply to Kathmandu Valley residents",
            status="closed",
            created_at=timezone.make_aware(datetime(2020, 1, 1)),
            first_public_date=timezone.make_aware(datetime(1998, 6, 1)),
        )
        
        src5 = DocumentSource.objects.create(
            title="Melamchi audit reports",
            description="Government audit reports showing cost escalations",
            source_type="government",
        )
        src6 = DocumentSource.objects.create(
            title="Melamchi news coverage",
            description="News reports documenting repeated delays and failures",
            source_type="media",
        )
        
        Evidence.objects.create(allegation=melamchi, source=src5, description="Government audit reports showing cost escalations", order=1)
        Evidence.objects.create(allegation=melamchi, source=src6, description="News reports documenting repeated delays and failures", order=2)
        
        Timeline.objects.create(allegation=melamchi, date=datetime(1998, 6, 1).date(), title="Project initiated", description="Melamchi project officially launched with 5-year completion target", order=1)
        Timeline.objects.create(allegation=melamchi, date=datetime(2021, 6, 15).date(), title="Flood damage halts operations", description="Monsoon floods severely damage tunnel and infrastructure", order=2)
        
        Modification.objects.create(allegation=melamchi, action="created", notes="Initial allegation created")
        
        # 4. KP Oli
        oli = Allegation.objects.create(
            allegation_type="broken_promise",
            state="current",
            title="KP Sharma Oli's Unfulfilled 2017 Election Promises",
            alleged_entities=["kp-sharma-oli"],
            related_entities=["nepal-communist-party", "nepal-government"],
            location_id="nepal",
            description="""# KP Sharma Oli's Broken Election Promises

## Overview
During the 2017 election campaign, KP Sharma Oli made several ambitious promises that remained unfulfilled during his tenure as Prime Minister.

## Key Broken Promises

### 1. Prosperity and Development
**Promise**: "We will make Nepal prosperous within 5 years"
**Reality**: Nepal's economic indicators showed minimal improvement; poverty rates remained high

### 2. Railway Connection
**Promise**: Railway connection to Kathmandu within his term
**Reality**: No significant progress on railway infrastructure

### 3. Employment
**Promise**: Create millions of jobs and stop youth migration
**Reality**: Youth migration continued at high rates; unemployment remained a critical issue

### 4. Corruption-Free Governance
**Promise**: Zero tolerance for corruption
**Reality**: Multiple corruption scandals emerged during his tenure""",
            key_allegations="Failed to deliver on prosperity promise; no railway to Kathmandu; continued youth migration; corruption scandals during tenure",
            status="closed",
            created_at=timezone.make_aware(datetime(2021, 7, 15)),
            first_public_date=timezone.make_aware(datetime(2017, 11, 15)),
        )
        
        src7 = DocumentSource.objects.create(
            title="Oli campaign speeches",
            description="Video recordings of election campaign speeches",
            source_type="social_media",
        )
        src8 = DocumentSource.objects.create(
            title="Economic data during Oli tenure",
            description="Economic data showing lack of promised development",
            source_type="government",
        )
        
        Evidence.objects.create(allegation=oli, source=src7, description="Video recordings of election campaign speeches", order=1)
        Evidence.objects.create(allegation=oli, source=src8, description="Economic data showing lack of promised development", order=2)
        
        Timeline.objects.create(allegation=oli, date=datetime(2017, 11, 15).date(), title="Election campaign promises", description="Oli makes ambitious promises during election rallies", order=1)
        Timeline.objects.create(allegation=oli, date=datetime(2021, 7, 13).date(), title="End of tenure", description="Oli's government falls; promises remain unfulfilled", order=2)
        
        Modification.objects.create(allegation=oli, action="created", notes="Initial allegation created")
        
        # 5. Media Trial
        media = Allegation.objects.create(
            allegation_type="media_trial",
            state="current",
            title="Sandeep Lamichhane Case: Media Trial and Public Opinion",
            alleged_entities=["nepali-media-houses"],
            related_entities=["sandeep-lamichhane"],
            location_id="kathmandu-district",
            description="""# Media Trial of Sandeep Lamichhane

## Overview
The rape case against cricketer Sandeep Lamichhane became subject to intense media coverage and public opinion formation before legal proceedings concluded.

## Media Conduct Issues

### Premature Judgment
Multiple media outlets published stories with presumptive language suggesting guilt before trial completion.

### Privacy Violations
Details of the case, including sensitive information, were widely circulated on social media and news platforms.

### Trial by Social Media
Public opinion was heavily influenced by media narratives rather than court proceedings, with both supporters and critics forming strong positions.

## Impact on Justice
The intense media coverage raised concerns about:
- Fair trial rights
- Presumption of innocence
- Influence on judicial proceedings
- Victim and accused privacy""",
            key_allegations="Extensive media coverage prejudicing fair trial; violation of privacy rights; formation of public opinion before legal conclusion; sensationalized reporting",
            status="closed",
            created_at=timezone.make_aware(datetime(2022, 9, 10)),
            first_public_date=timezone.make_aware(datetime(2022, 9, 8)),
        )
        
        src9 = DocumentSource.objects.create(
            title="Media coverage analysis",
            description="Collection of news articles with prejudicial language",
            source_type="social_media",
        )
        src10 = DocumentSource.objects.create(
            title="Media ethics analysis",
            description="Analysis by media ethics organizations",
            source_type="ngo",
        )
        
        Evidence.objects.create(allegation=media, source=src9, description="Collection of news articles with prejudicial language", order=1)
        Evidence.objects.create(allegation=media, source=src10, description="Analysis by media ethics organizations", order=2)
        
        Timeline.objects.create(allegation=media, date=datetime(2022, 9, 8).date(), title="Case becomes public", description="Rape allegations against Lamichhane become public; media frenzy begins", order=1)
        Timeline.objects.create(allegation=media, date=datetime(2024, 1, 10).date(), title="Court verdict delivered", description="District court delivers verdict after prolonged media coverage", order=2)
        
        Modification.objects.create(allegation=media, action="created", notes="Initial allegation created")
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created:'))
        self.stdout.write(f'  - {Allegation.objects.count()} allegations')
        self.stdout.write(f'  - {DocumentSource.objects.count()} document sources')
        self.stdout.write(f'  - {Evidence.objects.count()} evidence records')
        self.stdout.write(f'  - {Timeline.objects.count()} timeline entries')
        self.stdout.write(f'  - {Modification.objects.count()} modifications')
