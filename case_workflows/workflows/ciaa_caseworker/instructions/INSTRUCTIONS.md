## Caseworker instructions

You are an expert agentic workflow runner and you are helping build a fact-based database of corruption cases for Nepal. You are responsible for integral case drafting into the Jawafdehi system.

Follow the user stories strictly in `prd.json`.

Start by reading INSTRUCTIONS.md, then read `progress.json` to find the next incomplete story. Execute **exactly one** user story, then stop immediately. Do not plan or proceed to any subsequent stories.

NOTE: BEFORE starting your work, create a run summary file at `logs/run-summary-<date-time>.md` (use the current ISO 8601 datetime without colons, e.g. `logs/run-summary-2026-04-04T172904.md`). Record the single story you are about to execute. THEN, AFTER you have finished, update the same file with what you completed, any findings, and the outcome.

CRITICAL: After completing the story, emit exactly one progress marker to stdout and then exit:

```
WORKFLOW_PROGRESS: {"story": "US-XXX", "story_title": "...", "success": true, "notes": "...", "started": "<iso8601>", "completed": "<iso8601>"}
```

The workflow runner reads this marker to record progress and will invoke you again for the next story. Do **not** attempt to continue to the next story in the same invocation. If the story cannot be completed, emit `success: false` with a notes explanation. To abort the entire workflow, emit `WORKFLOW_FAILED: <reason>` instead.

**IMPORTANT:** Do **NOT** write to `progress.json` or `prd.json`. These files are managed exclusively by the workflow runner. You may only read them.

## Casework Folder Structure

Your working environment for each case is isolated within a unique case folder located at `casework/<case_number>`. This folder contains the following structure:

- `prd.json`: The Product Requirements Document containing the sequence of user stories/tasks you must follow.
- `progress.json`: Tracks which user stories are complete. Written by the workflow runner — do not edit directly.
- `logs/`: A directory for run summaries. Each agent invocation writes one `run-summary-<date-time>.md` file here.
- `instructions/`: A directory containing these instructions and potentially other reference materials.
- `sources/raw/`: A directory for storing raw source documents (like PDFs, HTML files, or images) before processing.
- `sources/markdown/`: A directory for storing the extracted or converted markdown versions of the source documents.

Any temporary files, drafts, or exported evidence for the case should be generated within this `casework/<case_number>` directory to keep the workspace organized.


## Collecting important information

### Case data

Use the `ngm_extract_case_data` tool to extract the full case data from the NGM database. You must save it in the casework folder as `sources/case_<case_number>_<date-time>.md`.

### CIAA Press releases
Find the CIAA press release for Special court case 081-CR-0123.

The CIAA press releases are located at URLs like https://ciaa.gov.np/pressrelease/2000. The press release ID seems to be sorted in ascending order.

Usually, CIAA press release are on the date when the case is filed to special court.

Download and save it at sources/raw/ciaa-press-release-<press-release-id>.pdf

Sample dates:
- https://ciaa.gov.np/pressrelease/1000: मिति २०७६/०१/१२ गते । 
- https://ciaa.gov.np/pressrelease/2000: मिति २०७८/०६/१९ गते ।
- https://ciaa.gov.np/pressrelease/3000: मिति २०८१/१२/१४ गते।

To download the file, use `curl` or equivalent tools.

> NOTE: CIAA press releases are also available in `data/ciaa-press-releases.csv` (columns: press_id, publication_date, title, source_url). Use `read_file` to read the CSV — do NOT use grep, as grep only returns file paths and not the matching line content. Find the row whose title contains the defendant name and read the source_url field.

Once you find the URL, check for .doc, .docx, or .pdf files in the web page. Use this url to download the file.

### Charge sheet.

Get the charge sheet for Special court case 081-CR-0123.

It needs to be collected from Attorney General website located at https://ag.gov.np/abhiyog.

Save it to sources/raw/charge-sheet-<case-number>.pdf

The publication date is usually when CIAA publishes the press release; it's also the same date when the Special court case is registered.

> NOTE: AG charge sheets are also available in `data/ag_index.csv` (columns: case_number, title, filing_date, pdf_url, court_office). Use `read_file` to read the CSV — do NOT use grep, as grep only returns file paths and not the matching line content. Find the row where case_number matches your case number and read the pdf_url field.

Once you identify the year and month, you can use a curl like this to download the charge sheet:

curl 'https://ag.gov.np/abhiyogpatras?month_id=50&code=sgao&description=undefined'.

The month ID is determined as follows:
2078 baisakh = 1
2078 Jestha = 2
...
2079 Baisakh = 13
...

### Bolpatra (Procurement Documents)

Get the bolpatra (procurement documents) for the case if applicable.

Bolpatra documents are procurement records from https://www.bolpatra.gov.np that may be referenced in the CIAA press release or charge sheet (abhiyog patra). These are only relevant for procurement-related corruption cases.

#### Step 1: Find IFB/RFP/EOI/PQ Numbers

Read through the CIAA press release and charge sheet to find procurement contract identifiers. Look for patterns like:

- **IFB/RFP/EOI/PQ No:** followed by a number
- **Contract No:** followed by a number
- **Common formats:**
  - `Re-PPHL2/G/NCB/02/2079-80`
  - `NITC/G/NCB-7-2074/75`
  - `ABC/DEF/123/2079-80`

These numbers typically appear in sections describing the procurement contract or project details.

**Note:** In many procurement-related cases, the Contract No listed in the charge sheet is identical to the IFB number (e.g., case 081-CR-0082 had "Contract No: Re-PPHL2/G/NCB/02/2079-80" which was also the IFB). Use your judgment to determine whether the Contract No is suitable to pass to fetch_bolpatra.py; if it returns no results, try variations or note it as unavailable.

**IMPORTANT - Handle Typos and Formatting Errors:**

IFB numbers in press releases or charge sheets may contain typos or formatting errors. For example:
- Document shows: `NITC/G/NCB-7-074/75` (missing digit in year)
- Correct format: `NITC/G/NCB-7-2074/75` (full 4-digit year)

If your initial search returns no results, try variations:
- Add missing digits to years (`074/75` → `2074/75`)
- Try different separators (dashes vs slashes)
- Check for transposed numbers or missing segments

#### Step 2: Use fetch_bolpatra.py Script

Once you have identified the IFB/RFP/EOI/PQ number, use the `fetch_bolpatra.py` script to automatically search and download all procurement documents:

```bash
python .agents/caseworker/etc/scripts/fetch_bolpatra.py "IFB_NUMBER"
```

**Example:**
```bash
python .agents/caseworker/etc/scripts/fetch_bolpatra.py "NITC/G/NCB-7-2074/75"
```

The script will:
1. Search bolpatra.gov.np for the IFB number
2. Extract tender IDs from search results
3. Fetch detailed tender information
4. Download all available documents (bid documents, addendums, LOI, etc.)
5. Save files to `.agents/caseworker/data/bolpatra/` directory

**After downloading**, move the files to your case folder:
```bash
mv .agents/caseworker/data/bolpatra/NITC-G-NCB-7-2074-75_*.pdf casework/<case_number>/sources/raw/
```

#### Step 3: Try Variations if No Results

If the script returns "No tenders found", try these variations:
- Add full 4-digit year: `NITC/G/NCB-7-2074/75` instead of `NITC/G/NCB-7-074/75`
- Try with 2-digit year: `NITC/G/NCB-7-74/75`
- Check for typos in the original document

#### Step 4: If No Procurement Documents Are Available

If:
- No IFB/RFP/EOI/PQ number is found in the CIAA or charge sheet documents, or
- The search returns no matching tender, or
- The tender exists but no downloadable files are available,

Then document this in the progress log and continue with the next user story. Not all corruption cases involve procurement.

### Court Orders (Faisala)

Get the court order (faisala) document for the case if available.

Use `court_identifier` and `case_number` from the existing case details file.

#### Step 1: Try Direct URL First (fast path)

Try these URLs first using `<court_identifier>` and `<case_number>`:

- `https://ngm-store.jawafdehi.org/uploads/court-orders/<court_identifier>/<case_number>.1.doc`
- `https://ngm-store.jawafdehi.org/uploads/court-orders/<court_identifier>/<case_number>.1.docx`
- `https://ngm-store.jawafdehi.org/uploads/court-orders/<court_identifier>/<case_number>.1.pdf`

If none exist, also try `.2` variants.

#### Step 2: Use Index Traversal Only If Direct URL Fails (fallback)

Start from:
`https://ngm-store.jawafdehi.org/index-v2.json`

Find `court-orders` and follow `$ref`, then traverse:

1. `court-orders`
2. `<court_identifier>`
3. year node:
   - If case number starts with a 3-digit BS year (e.g., `081-CR-0046`), use that as the year node (`081`).
   - Otherwise, derive year from `registration_date_bs`: months 1-3 → year-1, months 4-12 → year; use last 3 digits (e.g., `2081-09-22` → `081`).
   - If still not found, try adjacent years (year-1, year+1), then scan available year nodes for a match.
4. exact case node
5. use `manuscripts[].url` as the exact file URL

#### Step 3: Save and Convert

Save raw file to:
- `sources/raw/court-order-<case-number>.<ext>`

Convert and save markdown to:
- `sources/markdown/court-order-<case-number>.md`

#### Step 4: If Not Found

If both direct URL and index fallback fail, note this in the run summary and continue.

## Fetching news items from Web search

Use the web search tool to find and fetch relevant news items regarding the case from Web search. This helps build out the context and details of the allegations. Ensure you search using case details like case number, defendants' names, and the relevant court. Try searching near the court case registration date or the CIAA press release date.

If you are unable to discover any news items that's also fine. Just note it in your run summary and move on to the next user story. But please write a file called sources/markdown/news-search-results.md in the casework folder.

Also, for checkpoint, after every 10 or so web searches, keep updating the search results in sources/markdown/news-search-progress.md and note progress in your run summary.


## Preparing the Case Draft Locally
We'll create a markdown file called case-draft in the casework folder. It will follow the template added in `instructions/case-template.md` in the casework folder.

Use the jawafdehi-caseworker skill to review this case draft. NOTE explicitly that we won't have a case in Jawafdehi.org, so we will have to make do with the local files that we have. The review should be saved in the usual location, naming it review-<CIAA-case-number>-<date-time>.md.

## Creating a Basic Jawafdehi Case

Use the `create_jawafdehi_case` MCP tool with at minimum `title` and `case_type` (`CORRUPTION`).
You should also pass `short_description` if available.

The tool returns a JSON object. Record the integer `id` field (e.g. `42`) in `MEMORY.md` as the
**numeric Jawafdehi case ID**. This ID is required for all subsequent patch and upload operations.

After creating, immediately patch the case with `patch_jawafdehi_case` to set `key_allegations`,
`timeline`, `case_start_date`, and `case_end_date` from the draft.

## Creating / Updating Jawafdehi Entities

Use the entity MCP tools to link accused and related parties to the case. For each entity in
the draft (accused, organizations, locations):

1. **Search first** — call `search_jawaf_entities` with the entity's name. If a result matches,
   use its integer `id` and skip creation.

2. **Create if missing** — call `create_jawaf_entity` with either:
   - `nes_id`: the NES entity identifier (e.g. `entity:person/ram-prasad-sharma`) if known
   - `display_name`: a plain name string when no NES record exists
   Record the returned `id` in `MEMORY.md`.

3. **Link to the case** — call `patch_jawafdehi_case` with a JSON Patch `add` operation:
   ```json
   {"op": "add", "path": "/entities/-", "value": {"entity": <id>, "relationship_type": "<TYPE>", "notes": "<notes>"}}
   ```
   Relationship types: `ACCUSED` (main defendants), `ALLEGED` (named but unconfirmed),
   `RELATED` (organizations / third parties), `WITNESS`, `VICTIM`, `LOCATION`.

4. **Confirm** — call `get_jawaf_entity` with the entity ID and verify `related_cases` includes
   this case.

## Updating Remaining Case Details

### Step 1 — Upload source documents

Use `upload_document_source` to create a `DocumentSource` for each raw file. The tool reads the
file directly from disk — pass an absolute `file_path`, not base64 content.

**Supported extensions for raw sources**: `.pdf`, `.doc`, `.docx`, `.jpg`, `.jpeg`

For each file in `sources/raw/` with one of those extensions, call `upload_document_source`:

| filename prefix         | `source_type`        | `description` required? |
|-------------------------|----------------------|-------------------------|
| `ciaa-press-release-*`  | `OFFICIAL_GOVERNMENT`| Yes                     |
| `charge-sheet-*`        | `LEGAL_PROCEDURAL`   | Yes                     |
| `court-order-*`         | `LEGAL_COURT_ORDER`  | Yes                     |
| `bolpatra-*`            | `OFFICIAL_GOVERNMENT`| Yes                     |

Also upload every `sources/markdown/news-*.md` file with `source_type=MEDIA_NEWS`.

Example `description` for a charge sheet:
> "CIAA Charge Sheet — Case 081-CR-0123 filed on 2081-05-15 against Ram Prasad Sharma"

Record every returned `source_id` and its description in `MEMORY.md`.

### Step 2 — Attach evidence to the case

After all uploads, call `patch_jawafdehi_case` with one RFC 6902 `add` operation per source:

```json
{"op": "add", "path": "/evidence/-", "value": {"source_id": "<source_id>", "description": "<description>"}}
```

Combine all evidence `add` ops into a single `patch_jawafdehi_case` call.

### Step 3 — Update remaining case fields

Call `get_jawafdehi_case` first to see which fields are already populated. Then patch whatever
is missing from `draft.md`:

- `/timeline` — list of `{"date": "<ISO date AD>", "title": "...", "description": "..."}` objects
- `/short_description` — one-sentence teaser
- `/description` — full Nepali HTML description
- `/tags` — list of English tags
- `/key_allegations` — list of allegations
- `/case_start_date`, `/case_end_date` — ISO 8601 dates

Combine all field updates into a single `patch_jawafdehi_case` call.

