# Security

## Supported versions

Security fixes are made for the latest public release. Update to the latest version before reporting an issue where possible.

## Reporting a vulnerability

If this repository's **Security → Report a vulnerability** option is available, use it for private reports. Otherwise, open a minimal issue asking for a private reporting channel without disclosing exploit details or affected private data.

Include the version, a synthetic reproduction and expected/actual behaviour. Never attach API keys, real workbooks, invoices, personal data or unredacted logs.

## Security boundaries

- Runtime workbooks, settings, backups and PDFs are local plaintext files.
- A chosen cloud-synced export folder can disclose exported data to its provider and anyone with access to that folder.
- Mobile HTML contains embedded work data and must be treated as a private document.
- Desktop AI requests disclose the selected notes to Anthropic after explicit confirmation.
- Releases are unsigned; checksums detect differences from a published asset but do not replace publisher authentication.

See [PRIVACY.md](PRIVACY.md) for details and [CONTRIBUTING.md](CONTRIBUTING.md) for checks that protect release contents.
