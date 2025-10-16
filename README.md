# Gmail-TripIt Historic Import

A Python system for importing 20+ years of historical flight confirmations from Gmail to TripIt. This implementation follows the comprehensive specifications in [spec.md](spec.md).

## Features

- **Two-Phase Workflow**: 
  - Phase 1: Search, classify, parse, and label flight confirmation emails
  - Phase 2: Forward labeled emails to TripIt
- **Multi-Strategy Parsing**: Schema.org markup → HTML tables → Regex fallback
- **Duplicate Detection**: Fuzzy PNR matching to avoid duplicate submissions
- **State Management**: SQLite-based tracking to enable resumption and prevent re-processing
- **Dry-Run Mode**: Test the entire workflow without making any changes
- **Comprehensive Logging**: Detailed logs with rotation for debugging and monitoring

## Installation

1. **Clone the repository**:
```bash
git clone https://github.com/TylerLeonhardt/gmail-tripit-historic-import.git
cd gmail-tripit-historic-import
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Setup Gmail API credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials and save as `config/credentials.json`

## Usage

### Quick Start

The easiest way to run the system is using the `run.py` wrapper:

```bash
# Show help
python run.py --help

# Test with dry-run (recommended first step)
python run.py --phase 1 --dry-run

# Actually run Phase 1
python run.py --phase 1
```

Alternatively, you can run it as a module:

```bash
# From the project root with src in PYTHONPATH
PYTHONPATH=src python -m flight_processor.main --help
```

### Dry-Run Mode (Recommended First Step)

Test the system without making any changes:

```bash
# Test Phase 1: Search and classify emails
python run.py --phase 1 --dry-run

# Test Phase 2: Forward emails
python run.py --phase 2 --dry-run

# Test both phases
python run.py --phase all --dry-run
```

### Phase 1: Label Flight Confirmation Emails

Search for flight emails, classify them, parse details, and apply a Gmail label:

```bash
python run.py --phase 1
```

This will:
1. Search your Gmail using an optimized query for flight confirmations
2. Classify each email using multiple strategies
3. Parse flight details (PNR, flight number, airports, etc.)
4. Apply the label "Flight Confirmations - To Review"
5. Save all data to SQLite for tracking

**Review the labeled emails** in Gmail before proceeding to Phase 2!

### Phase 2: Forward to TripIt

Forward labeled emails to TripIt's parsing service:

```bash
python run.py --phase 2
```

This will:
1. Get all successfully labeled emails from Phase 1
2. Deduplicate based on PNR to avoid duplicate trips
3. Forward unique emails to plans@tripit.com
4. Track forwarding status in the database

### Show Statistics

```bash
python run.py --stats
```

### Custom Options

```bash
# Custom search query
python run.py --phase 1 --query "from:united.com after:2020/01/01"

# Custom label name
python run.py --phase 1 --label-name "My Flight Emails"

# Skip deduplication
python run.py --phase 2 --no-deduplicate

# Change log level
python run.py --log-level DEBUG
```

## Project Structure

```
gmail-tripit-historic-import/
├── README.md                          # This file
├── spec.md                            # Detailed specification
├── requirements.txt                   # Python dependencies
├── .gitignore                         # Git ignore rules
├── config/
│   ├── .env.example                   # Environment variables template
│   ├── settings.py                    # Configuration settings
│   └── credentials.json               # Gmail API credentials (not in repo)
├── src/
│   └── flight_processor/
│       ├── __init__.py
│       ├── main.py                    # Main CLI entry point
│       ├── auth/                      # Gmail authentication
│       ├── search/                    # Email search with pagination
│       ├── parsers/                   # Flight email classification & parsing
│       ├── dedup/                     # Duplicate detection
│       ├── forward/                   # Email forwarding & labeling
│       ├── state/                     # SQLite state management
│       └── utils/                     # Logging, retry, dry-run utilities
├── tests/                             # Comprehensive test suite
│   ├── test_classifier.py
│   ├── test_parser.py
│   ├── test_deduplicator.py
│   ├── test_state_manager.py
│   └── test_dry_run.py
├── data/                              # SQLite database (created on first run)
└── logs/                              # Log files (created on first run)
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=flight_processor --cov-report=html

# Run specific test file
pytest tests/test_classifier.py

# Run with verbose output
pytest -v
```

## How It Works

### Phase 1: Email Detection and Labeling

1. **Search**: Uses Gmail API to search for emails matching flight confirmation patterns
2. **Classify**: Multi-strategy classification with scoring:
   - Schema.org FlightReservation markup (+50 points)
   - Known airline domain (+20 points)
   - Confirmation subject pattern (+20 points)
   - Flight markers in content (+10 points)
   - Threshold: 50+ points = flight confirmation
3. **Parse**: Extract flight details using fallback strategies:
   - Schema.org JSON-LD or Microdata (cleanest)
   - HTML table parsing (structured)
   - Regex patterns (fallback for older emails)
4. **Label**: Apply Gmail label using batch operations (1000 messages/call)
5. **Store**: Save metadata and parsing results to SQLite

### Phase 2: Deduplication and Forwarding

1. **Load**: Get all successfully labeled emails from database
2. **Deduplicate**: Fuzzy PNR matching (95% similarity threshold)
3. **Forward**: Send emails to plans@tripit.com in batches
4. **Track**: Record forwarding status for each email

### Dry-Run Mode

When `--dry-run` is specified:
- All API operations log what would happen but don't execute
- No emails are labeled or forwarded
- No database writes occur for actual operations
- Perfect for testing queries and validating logic

## Rate Limits and Performance

- **Gmail API Quota**: 1,200,000 units/minute (project), 15,000 units/minute (user)
- **Gmail Sending Limit**: 2,000 emails/day for standard accounts
- **Expected Performance**:
  - Phase 1 (1000-5000 emails): 5-10 minutes
  - Phase 2 (2000 emails): 2-3 days due to sending limit

## Configuration

Edit `config/settings.py` or create `.env` file based on `.env.example`:

- `SEARCH_QUERY`: Gmail search query for finding flight emails
- `TRIPIT_EMAIL`: TripIt email address (default: plans@tripit.com)
- `DB_PATH`: SQLite database location
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `BATCH_SIZE`: Messages per batch for labeling (max 1000)
- `FORWARD_BATCH_SIZE`: Messages per batch for forwarding

## Troubleshooting

### Authentication Issues

If you get authentication errors:
1. Delete `config/token.json`
2. Ensure `config/credentials.json` is valid
3. Re-run the script to trigger OAuth flow

### No Emails Found

- Check your search query with Gmail's web interface first
- Try a smaller date range: `after:2023/01/01`
- Use `--log-level DEBUG` to see detailed search info

### Parsing Failures

- The system uses multiple fallback strategies
- Expect 5-10% parse failure rate for very old emails
- Review logs to see which strategy worked for each email

### Rate Limiting

- The system includes automatic exponential backoff
- If you hit limits, wait a few minutes and re-run
- State tracking ensures no duplicate work

## Contributing

Contributions welcome! Please:
1. Write tests for new features
2. Follow existing code style
3. Update documentation
4. Test with dry-run mode first

## License

MIT

## Acknowledgments

Based on the comprehensive specification in [spec.md](spec.md), which provides detailed guidance on Gmail API usage, email parsing strategies, duplicate detection, and TripIt integration.