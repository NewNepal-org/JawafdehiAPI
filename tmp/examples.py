from datetime import datetime
from jawaf_models2 import (
    Allegation,
    AllegationType,
    AllegationLifecycleState,
    AllegationStatus,
    Evidence,
    EvidenceSourceType,
    TimelineEvent,
    Response,
    ModificationEntry,
    ModificationAction,
)

# 1. CORRUPTION - Lalita Niwas land grab case
corruption_allegation = Allegation(
    allegation_type=AllegationType.CORRUPTION,
    state=AllegationLifecycleState.CURRENT,
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
Multiple government officials, including former ministers and land revenue officers, are accused of facilitating the illegal transfer through document forgery and abuse of authority.
""",
    key_allegatioons="Illegal transfer of 175 ropanis of government land through forged documents; involvement of high-ranking officials; estimated loss of NPR 3+ billion to state",
    status=AllegationStatus.UNDER_INVESTIGATION,
    evidences=[
        Evidence(
            evidence_id="ev-lalita-001",
            description="CIAA investigation report documenting forged land ownership certificates",
            url="https://ciaa.gov.np/reports/lalita-niwas",
            source_type=EvidenceSourceType.GOVERNMENT,
        ),
        Evidence(
            evidence_id="ev-lalita-002",
            description="Supreme Court order to investigate the land transfer",
            url="https://supremecourt.gov.np/cases/lalita-niwas",
            source_type=EvidenceSourceType.GOVERNMENT,
        ),
    ],
    timeline=[
        TimelineEvent(
            date=datetime(2018, 3, 15),
            title="CIAA begins investigation",
            description="Commission for Investigation of Abuse of Authority initiates probe into illegal land transfers",
            evidence_ids=["ev-lalita-001"],
            source_url="https://ciaa.gov.np/news/2018-03-15",
        ),
        TimelineEvent(
            date=datetime(2020, 7, 12),
            title="Arrest warrants issued",
            description="CIAA issues arrest warrants for multiple officials including former ministers",
            evidence_ids=["ev-lalita-001"],
            source_url="https://ciaa.gov.np/news/2020-07-12",
        ),
    ],
    created_at=datetime(2018, 3, 10),
    first_public_date=datetime(2018, 3, 15),
    responses=[],
    modification_trail=[
        ModificationEntry(
            action=ModificationAction.CREATED,
            timestamp=datetime(2018, 3, 10),
            actor="system",
            notes="Initial allegation created",
        ),
    ],
)

# 2. MISCONDUCT - Rabi Lamichhane citizenship controversy
misconduct_allegation = Allegation(
    allegation_type=AllegationType.MISCONDUCT,
    state=AllegationLifecycleState.CURRENT,
    title="Rabi Lamichhane Citizenship and Cooperative Fraud Case",
    alleged_entities=["rabi-lamichhane"],
    related_entities=["rastriya-swatantra-party", "supreme-court-nepal"],
    location_id="kathmandu-district",
    description="""# Rabi Lamichhane Citizenship and Cooperative Fraud

## Overview
Allegations against Rabi Lamichhane, President of Rastriya Swatantra Party and former Deputy Prime Minister, involving citizenship irregularities and misappropriation of cooperative funds.

## Citizenship Issue
Questions raised about the validity of his Nepali citizenship certificate, with allegations that he held US citizenship while obtaining Nepali citizenship, which is not permitted under Nepali law.

## Cooperative Fraud
Allegations of embezzlement of funds from multiple savings and credit cooperatives, with victims claiming losses of hundreds of millions of rupees.
""",
    key_allegatioons="Fraudulent citizenship acquisition; embezzlement of cooperative funds; abuse of public office",
    status=AllegationStatus.UNDER_INVESTIGATION,
    evidences=[
        Evidence(
            evidence_id="ev-rabi-001",
            description="Supreme Court ruling on citizenship case",
            url="https://supremecourt.gov.np/cases/rabi-citizenship",
            source_type=EvidenceSourceType.GOVERNMENT,
        ),
        Evidence(
            evidence_id="ev-rabi-002",
            description="Cooperative victims' testimonies and financial records",
            source_type=EvidenceSourceType.CROWDSOURCED,
        ),
    ],
    timeline=[
        TimelineEvent(
            date=datetime(2023, 11, 28),
            title="Supreme Court orders citizenship investigation",
            description="Supreme Court directs authorities to investigate citizenship irregularities",
            evidence_ids=["ev-rabi-001"],
            source_url="https://supremecourt.gov.np/news/2023-11-28",
        ),
        TimelineEvent(
            date=datetime(2024, 1, 18),
            title="Arrested in cooperative fraud case",
            description="Police arrest Lamichhane in connection with cooperative embezzlement",
            evidence_ids=["ev-rabi-002"],
        ),
    ],
    created_at=datetime(2023, 11, 20),
    first_public_date=datetime(2023, 11, 28),
    responses=[],
    modification_trail=[
        ModificationEntry(
            action=ModificationAction.CREATED,
            timestamp=datetime(2023, 11, 20),
            actor="system",
        ),
    ],
)

# 3. BREACH_OF_TRUST - Melamchi Water Supply Project delays
breach_of_trust_allegation = Allegation(
    allegation_type=AllegationType.BREACH_OF_TRUST,
    state=AllegationLifecycleState.CURRENT,
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
Citizens were promised reliable water supply for over two decades, with multiple governments failing to deliver despite massive public investment.
""",
    key_allegatioons="26+ years of delays; cost overrun from NPR 16B to NPR 100B+; failure to deliver promised water supply to Kathmandu Valley residents",
    status=AllegationStatus.CLOSED,
    evidences=[
        Evidence(
            evidence_id="ev-melamchi-001",
            description="Government audit reports showing cost escalations",
            source_type=EvidenceSourceType.GOVERNMENT,
        ),
        Evidence(
            evidence_id="ev-melamchi-002",
            description="News reports documenting repeated delays and failures",
            source_type=EvidenceSourceType.SOCIAL_MEDIA,
        ),
    ],
    timeline=[
        TimelineEvent(
            date=datetime(1998, 6, 1),
            title="Project initiated",
            description="Melamchi project officially launched with 5-year completion target",
            evidence_ids=["ev-melamchi-001"],
        ),
        TimelineEvent(
            date=datetime(2021, 6, 15),
            title="Flood damage halts operations",
            description="Monsoon floods severely damage tunnel and infrastructure",
            evidence_ids=["ev-melamchi-002"],
        ),
    ],
    created_at=datetime(2020, 1, 1),
    first_public_date=datetime(1998, 6, 1),
    responses=[],
    modification_trail=[
        ModificationEntry(
            action=ModificationAction.CREATED,
            timestamp=datetime(2020, 1, 1),
            actor="system",
        ),
    ],
)

# 4. BROKEN_PROMISE - KP Sharma Oli's election promises
broken_promise_allegation = Allegation(
    allegation_type=AllegationType.BROKEN_PROMISE,
    state=AllegationLifecycleState.CURRENT,
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
**Reality**: Multiple corruption scandals emerged during his tenure
""",
    key_allegatioons="Failed to deliver on prosperity promise; no railway to Kathmandu; continued youth migration; corruption scandals during tenure",
    status=AllegationStatus.CLOSED,
    evidences=[
        Evidence(
            evidence_id="ev-oli-001",
            description="Video recordings of election campaign speeches",
            source_type=EvidenceSourceType.SOCIAL_MEDIA,
        ),
        Evidence(
            evidence_id="ev-oli-002",
            description="Economic data showing lack of promised development",
            source_type=EvidenceSourceType.GOVERNMENT,
        ),
    ],
    timeline=[
        TimelineEvent(
            date=datetime(2017, 11, 15),
            title="Election campaign promises",
            description="Oli makes ambitious promises during election rallies",
            evidence_ids=["ev-oli-001"],
        ),
        TimelineEvent(
            date=datetime(2021, 7, 13),
            title="End of tenure",
            description="Oli's government falls; promises remain unfulfilled",
            evidence_ids=["ev-oli-002"],
        ),
    ],
    created_at=datetime(2021, 7, 15),
    first_public_date=datetime(2017, 11, 15),
    responses=[],
    modification_trail=[
        ModificationEntry(
            action=ModificationAction.CREATED,
            timestamp=datetime(2021, 7, 15),
            actor="system",
        ),
    ],
)

# 5. MEDIA_TRIAL - Sandeep Lamichhane rape case
media_trial_allegation = Allegation(
    allegation_type=AllegationType.MEDIA_TRIAL,
    state=AllegationLifecycleState.CURRENT,
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
- Victim and accused privacy
""",
    key_allegatioons="Extensive media coverage prejudicing fair trial; violation of privacy rights; formation of public opinion before legal conclusion; sensationalized reporting",
    status=AllegationStatus.CLOSED,
    evidences=[
        Evidence(
            evidence_id="ev-media-001",
            description="Collection of news articles with prejudicial language",
            source_type=EvidenceSourceType.SOCIAL_MEDIA,
        ),
        Evidence(
            evidence_id="ev-media-002",
            description="Analysis by media ethics organizations",
            source_type=EvidenceSourceType.NGO,
        ),
    ],
    timeline=[
        TimelineEvent(
            date=datetime(2022, 9, 8),
            title="Case becomes public",
            description="Rape allegations against Lamichhane become public; media frenzy begins",
            evidence_ids=["ev-media-001"],
        ),
        TimelineEvent(
            date=datetime(2024, 1, 10),
            title="Court verdict delivered",
            description="District court delivers verdict after prolonged media coverage",
            evidence_ids=["ev-media-001", "ev-media-002"],
        ),
    ],
    created_at=datetime(2022, 9, 10),
    first_public_date=datetime(2022, 9, 8),
    responses=[],
    modification_trail=[
        ModificationEntry(
            action=ModificationAction.CREATED,
            timestamp=datetime(2022, 9, 10),
            actor="system",
        ),
    ],
)

# Export all allegations
allegations = [
    corruption_allegation,
    misconduct_allegation,
    breach_of_trust_allegation,
    broken_promise_allegation,
    media_trial_allegation,
]

if __name__ == "__main__":
    print("Created 5 allegations:")
    for allegation in allegations:
        print(f"- {allegation.allegation_type.value}: {allegation.title}")
