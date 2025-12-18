"""Prompts and schemas for AI extraction."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..agni_models import DocumentMetadata, ResolvedEntity, EntityMatchState

if TYPE_CHECKING:
    from ..agni_models import Conversation

# System prompt template for AI role and context
SYSTEM_PROMPT_TEMPLATE = """You are a world-class data researcher and analyst working on Jawafdehi (जवाफदेही), Nepal's premier civic technology platform for promoting transparency and accountability in governance.

## Your Mission
You specialize in extracting structured information from Nepali government documents, corruption cases, and accountability reports. Your work directly supports citizens' right to information and helps combat corruption by making government data accessible and searchable.

## Current Task: {extraction_type_description}

## Your Expertise
- **Nepali Context**: You have deep knowledge of Nepal's government structure, political landscape, and administrative systems
- **Bilingual Proficiency**: You excel at processing documents in both English and Nepali (Devanagari script)
- **Entity Recognition**: You can identify and classify people, organizations, locations, events, amounts, and dates with high accuracy
- **Corruption Analysis**: You understand patterns in corruption cases, investigation procedures, and accountability mechanisms
- **Data Quality**: You maintain the highest standards for data accuracy, completeness, and reliability

## Key Principles
- **Accuracy First**: Extract only information that is explicitly stated or clearly implied in the document
- **Cultural Sensitivity**: Respect Nepali naming conventions, organizational hierarchies, and cultural context
- **Transparency**: Provide confidence scores and reasoning for your extractions
- **Completeness**: Identify all relevant entities while avoiding false positives
- **Consistency**: Use standardized formats and classifications across all extractions

## Document Types You Handle
- Investigation reports and audit findings
- Government correspondence and official letters
- Court cases and legal documents
- Budget documents and financial statements
- Policy documents and regulations
- Meeting minutes and announcements
- News reports and media coverage
- Contracts and agreements
- Corruption case files

## Your Output Standards
- Provide confidence scores between 0.0 and 1.0 for all extractions
- Include both English and Nepali names when available
- Use proper entity classifications and sub-types
- Extract structured data with consistent formatting

{additional_context}

Remember: Your work helps build Nepal's most comprehensive database of governance and accountability information, empowering citizens with the transparency they deserve."""


def build_system_prompt(
    extraction_type: str = "full",
    guidance: Optional[str] = None,
    metadata_context: Optional[DocumentMetadata] = None,
    entity_context: Optional[EntityMatchState] = None,
) -> str:
    """Build system prompt with task-specific context.

    Args:
        extraction_type: Type of extraction being performed
        guidance: Optional guidance for extraction
        metadata_context: Optional metadata for context
        entity_context: Optional entity for updates

    Returns:
        Formatted system prompt string
    """
    # Define extraction type descriptions
    extraction_descriptions = {
        "metadata": "Document Metadata Extraction - Extract comprehensive metadata including title, author, publication date, document type, and source",
        "entities": "Entity Extraction - Identify and classify all relevant people, organizations, locations, events, documents, amounts, and dates",
        "entity_update": "Entity Update - Refine existing entity information based on user feedback and additional context",
        "full": "Complete Document Analysis - Extract both metadata and entities with comprehensive coverage"
    }
    
    extraction_type_description = extraction_descriptions.get(extraction_type, extraction_descriptions["full"])
    
    # Build additional context
    additional_context_parts = []
    
    if guidance:
        additional_context_parts.append(f"## Special Guidance\n{guidance}")
    
    if metadata_context and extraction_type == "entities":
        additional_context_parts.append("## Document Context")
        if metadata_context.title:
            additional_context_parts.append(f"- **Title**: {metadata_context.title}")
        if metadata_context.author:
            additional_context_parts.append(f"- **Author**: {metadata_context.author}")
        if metadata_context.document_type:
            additional_context_parts.append(f"- **Type**: {metadata_context.document_type}")
    
    if entity_context and extraction_type == "entity_update":
        additional_context_parts.append("## Entity Being Updated")
        additional_context_parts.append(f"- **Type**: {entity_context.entity_type}")
        if entity_context.entity_subtype:
            additional_context_parts.append(f"- **Sub-type**: {entity_context.entity_subtype}")
        if entity_context.resolved_entity:
            additional_context_parts.append(f"- **Current Names**: {entity_context.resolved_entity.names}")
    
    additional_context = "\n".join(additional_context_parts) if additional_context_parts else ""
    
    return SYSTEM_PROMPT_TEMPLATE.format(
        extraction_type_description=extraction_type_description,
        additional_context=additional_context
    )

# Extraction schema for structured data
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "metadata": DocumentMetadata.get_genai_extraction_schema(),
        "entities": {
            "type": "array",
            "items": ResolvedEntity.get_genai_extraction_schema()
        }
    },
    "required": ["metadata", "entities"]
}


def build_prompt(
    content: str,
    guidance: Optional[str] = None,
    conversation: Optional['Conversation'] = None,
    extraction_type: str = "full",
    metadata_context: Optional[DocumentMetadata] = None,
    entity_context: Optional[EntityMatchState] = None,
) -> str:
    """Build extraction prompt with content, guidance, and conversation history.

    Args:
        content: Document text content
        guidance: Optional guidance for extraction
        conversation: Optional conversation history for context
        extraction_type: Type of extraction being performed
        metadata_context: Optional metadata for context
        entity_context: Optional entity for updates

    Returns:
        Formatted prompt string with task-specific instructions (system prompt is passed separately)
    """
    prompt_parts = []

    # Task-specific instruction
    if extraction_type == "metadata":
        prompt_parts.append(
            "\n## Current Task: Metadata Extraction\n"
            "Extract comprehensive metadata from the document below. Focus on:\n"
            "- Document title (in original language)\n"
            "- Brief but informative summary of key content\n"
            "- Author or publishing organization\n"
            "- Publication or creation date\n"
            "- Document type classification\n"
            "- Source or originating entity"
        )
    elif extraction_type == "entities":
        prompt_parts.append(
            "\n## Current Task: Entity Extraction\n"
            "Extract all relevant entities from the document below. Focus on:\n"
            "- **People**: Politicians, civil servants, business persons, activists, journalists\n"
            "- **Organizations**: Government bodies, political parties, NGOs, companies\n"
            "- **Locations**: Provinces, districts, municipalities, specific buildings\n"
            "- **Events**: Corruption cases, investigations, court cases, meetings\n"
            "- **Documents**: Reports, contracts, policies, legal documents\n"
            "- **Amounts**: Financial figures, budgets, fines, compensation\n"
            "- **Dates**: Important timeline events and deadlines"
        )
    elif extraction_type == "entity_update":
        prompt_parts.append(
            "\n## Current Task: Entity Update\n"
            "Refine the entity information based on user conversation and document context. "
            "Maintain accuracy while incorporating user feedback and additional context."
        )
    else:
        prompt_parts.append(
            "\n## Current Task: Complete Document Analysis\n"
            "Perform comprehensive extraction of both metadata and entities from the document. "
            "Ensure all governance, corruption, and accountability-related information is captured."
        )

    # Add specific Nepali context for this document
    prompt_parts.append(
        "\n## Document Context\n"
        "This document originates from Nepal's governance ecosystem. Apply your expertise in:\n"
        "- **Language Processing**: Handle both Devanagari (नेपाली) and romanized Nepali text\n"
        "- **Government Structure**: Recognize federal, provincial, and local government entities\n"
        "- **Political Landscape**: Identify political parties, leaders, and electoral contexts\n"
        "- **Administrative Divisions**: Classify provinces, districts, municipalities, and wards\n"
        "- **Financial Context**: Process amounts in Nepali Rupees (NPR) and budget allocations\n"
        "- **Legal Framework**: Understand corruption laws, investigation procedures, and court systems"
    )

    # Add project-specific guidance
    if guidance:
        prompt_parts.append(f"\n## Special Guidance\n{guidance}")

    # Add metadata context for entity extraction
    if metadata_context and extraction_type == "entities":
        prompt_parts.append("\n## Document Metadata Context")
        if metadata_context.title:
            prompt_parts.append(f"**Title**: {metadata_context.title}")
        if metadata_context.author:
            prompt_parts.append(f"**Author**: {metadata_context.author}")
        if metadata_context.document_type:
            prompt_parts.append(f"**Document Type**: {metadata_context.document_type}")
        if metadata_context.publication_date:
            prompt_parts.append(f"**Publication Date**: {metadata_context.publication_date}")

    # Add entity context for updates
    if entity_context and extraction_type == "entity_update":
        prompt_parts.append("\n## Entity Being Updated")
        prompt_parts.append(f"**Type**: {entity_context.entity_type}")
        if entity_context.entity_subtype:
            prompt_parts.append(f"**Sub-type**: {entity_context.entity_subtype}")
        if entity_context.resolved_entity:
            prompt_parts.append(f"**Current Names**: {entity_context.resolved_entity.names}")
            if entity_context.resolved_entity.attributes:
                prompt_parts.append(
                    f"**Current Attributes**: {entity_context.resolved_entity.attributes}"
                )

    # Add conversation history if provided
    if conversation and conversation.thread:
        user_messages = [msg.text for msg in conversation.thread if msg.author.value == "user"]
        if user_messages:
            prompt_parts.append("\n## User Conversation History")
            for i, msg in enumerate(user_messages, 1):
                prompt_parts.append(f"**Message {i}**: {msg}")

    # Add document content
    prompt_parts.append(f"\n## Document to Analyze\n\n{content}")

    # Add final extraction instructions
    prompt_parts.append(
        "\n## Extraction Instructions\n"
        "- Follow the JSON schema exactly as provided\n"
        "- For Nepali entities, provide names in both Devanagari and romanized forms when available\n"
        "- Include attributes with relevant structured information (positions, amounts, dates, etc.)\n"
        "- Only extract information that is explicitly stated or clearly implied in the document\n"
        "- Maintain high standards for accuracy and completeness"
    )

    return "\n".join(prompt_parts)