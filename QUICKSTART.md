# Gmail-TripIt Historic Import - Quick Start Guide

This guide will walk you through using the system for the first time.

## Prerequisites

1. Python 3.8 or higher installed
2. A Gmail account with flight confirmation emails
3. A TripIt account

## Step 1: Setup

```bash
# Clone the repository
git clone https://github.com/TylerLeonhardt/gmail-tripit-historic-import.git
cd gmail-tripit-historic-import

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Gmail API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the Gmail API:
   - Click "Enable APIs and Services"
   - Search for "Gmail API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "Credentials" in the sidebar
   - Click "Create Credentials" → "OAuth client ID"
   - Select "Desktop application"
   - Name it (e.g., "Gmail Flight Importer")
   - Click "Create"
5. Download the credentials:
   - Click the download icon next to your new OAuth client
   - Save the file as `config/credentials.json`

## Step 3: Test with Dry-Run

Before making any changes, test with dry-run mode:

```bash
# Test searching and classifying emails (no changes made)
python run.py --phase 1 --dry-run --query "from:united.com after:2023/01/01"

# Review the logs
tail -100 logs/processor.log
```

The dry-run will:
- Authenticate with Gmail (one-time OAuth flow)
- Search for matching emails
- Classify them as flight confirmations
- Parse flight details
- Show what would be labeled (but NOT actually label)

Expected output:
```
Gmail-TripIt Historic Import System
Dry-run mode: True
Searching emails with query: from:united.com after:2023/01/01...
Found 50 total messages
✓ Flight confirmation detected: Your United Flight Confirmation
  Parsed: PNR=ABC123, Flight=UA456
[DRY-RUN] Would call apply_label_to_messages...
Phase 1 complete!
```

## Step 4: Run Phase 1 (Label Emails)

If the dry-run looks good, run it for real:

```bash
# Label all flight confirmations from the last 2 years
python run.py --phase 1 --query "after:2022/01/01"
```

This will:
1. Search your Gmail for flight emails (2022-present)
2. Classify and parse each one
3. Apply the label "Flight Confirmations - To Review"
4. Save metadata to SQLite database

**Review the labeled emails in Gmail!** Go to the label and verify:
- Are these all flight confirmations? (few false positives)
- Are any flight emails missing? (check unlabeled emails)

## Step 5: Test Phase 2 with Dry-Run

Before forwarding to TripIt, test again:

```bash
# Test forwarding (no actual forwarding)
python run.py --phase 2 --dry-run
```

This will:
- Load all labeled emails from database
- Deduplicate based on PNR
- Show what would be forwarded to TripIt

## Step 6: Forward to TripIt

If everything looks good:

```bash
# Forward unique emails to TripIt
python run.py --phase 2
```

**Note:** Gmail limits to 2,000 emails/day. For large imports:
- The system will forward in batches
- You may need to run over multiple days
- Progress is tracked in the database

## Step 7: Check TripIt

1. Log in to your TripIt account
2. Check for new trips appearing
3. Review TripIt notification emails for any parsing failures

## Troubleshooting

### "No module named 'googleapiclient'"
Install dependencies: `pip install -r requirements.txt`

### "credentials.json not found"
Follow Step 2 to set up Gmail API credentials

### No emails found
- Try a broader query: `python run.py --phase 1 --query "after:2020/01/01"`
- Test your query in Gmail web interface first
- Use `--log-level DEBUG` for detailed info

### Authentication failed
- Delete `config/token.json` and try again
- Check that `config/credentials.json` is valid

## Advanced Usage

### Custom Search Queries

```bash
# Specific airline and date range
python run.py --phase 1 --query "from:delta.com after:2020/01/01 before:2024/01/01"

# Multiple airlines
python run.py --phase 1 --query "(from:united.com OR from:delta.com) after:2022/01/01"

# Subject-based search
python run.py --phase 1 --query "subject:confirmation after:2020/01/01"
```

### Custom Label

```bash
python run.py --phase 1 --label-name "My Flight Emails"
```

### Skip Deduplication

```bash
# Forward all emails, including duplicates
python run.py --phase 2 --no-deduplicate
```

### Detailed Logging

```bash
python run.py --phase 1 --log-level DEBUG
tail -f logs/processor.log
```

### Check Statistics

```bash
python run.py --stats
```

Output:
```
PROCESSING STATISTICS
PHASE1_LABEL        | SUCCESS    |   1234
PHASE1_LABEL        | SKIPPED    |    567
PHASE1_LABEL        | FAILED     |     23
PHASE2_FORWARD      | SUCCESS    |   1100
```

## Processing Large Email Archives

For 20+ years of email (5000+ messages):

### Week 1: Test and Refine
```bash
# Day 1-2: Test with recent emails
python run.py --phase 1 --query "after:2023/01/01" --dry-run
python run.py --phase 1 --query "after:2023/01/01"

# Review, adjust thresholds if needed
# Check TripIt parsing success rate
python run.py --phase 2 --dry-run
python run.py --phase 2
```

### Week 2: Expand Date Range
```bash
# Day 3-4: 2020-2022
python run.py --phase 1 --query "after:2020/01/01 before:2023/01/01"
python run.py --phase 2

# Day 5-7: Earlier years in chunks
python run.py --phase 1 --query "after:2015/01/01 before:2020/01/01"
python run.py --phase 2
```

### Week 3: Historical
```bash
# Oldest emails (may have lower parse success)
python run.py --phase 1 --query "after:2000/01/01 before:2015/01/01"
python run.py --phase 2
```

## Tips

1. **Start Small**: Test with 1-2 years first
2. **Review Labels**: Always review Phase 1 results before Phase 2
3. **Check TripIt**: Monitor TripIt for parsing failures
4. **Save Logs**: Keep logs for troubleshooting
5. **Backup Database**: Copy `data/state.db` periodically

## Next Steps

- Review parsed trips in TripIt
- Handle any parsing failures manually
- Re-run for new emails periodically
- Adjust search queries based on your airlines

## Getting Help

Check the logs first:
```bash
tail -100 logs/processor.log
```

For issues:
1. Check the main README.md
2. Review spec.md for detailed technical information
3. Open an issue on GitHub
