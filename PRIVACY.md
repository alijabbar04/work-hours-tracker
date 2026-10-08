# Privacy and your data

Work Hours Tracker starts with an empty tracker. This repository and its release package contain application code, public assets and documentation, not a user's workbook, settings, invoices, API key or work history.

## Local storage

Ordinary tracking runs on your computer. There is no app account, analytics, advertising, automatic telemetry or automatic update connection. On Windows, the default data folder is `%LOCALAPPDATA%\WorkHoursTracker`.

Your workbook, backups, configuration and PDF invoices are **unencrypted files**. They may contain work notes, rates, names, addresses and payment details you entered. Other people or software with access to your files can read them. Protect the computer account and your backups appropriately.

Desktop API keys are stored through a supported secure operating-system keyring; `ANTHROPIC_API_KEY` is also supported. No plaintext key fallback is provided. Environment variables are accessible to processes running with appropriate access to your account, so treat them as secrets.

## Optional folder exports

Mirroring is off until you choose a folder. The workbook mirror includes the workbook's hours, rates and work summaries. If the folder belongs to OneDrive, Dropbox or another sync provider, that provider can receive the files under its own terms and privacy policy. The app copies files to the folder; it does not connect to that provider's API.

Invoice mirroring is separately disabled by default. PDFs can contain your personal, client and bank details. Enable it only for a private folder you control.

Mobile HTML exports are disabled by default. When enabled, the generated file contains dates, hours, rates and work summaries. Including invoice, client, payment details and invoice notes requires another opt-in. The mobile file has no AI integration, API key storage or remote requests. Anyone who receives the HTML can inspect its embedded data, even without the desktop app.

Phone entry JSON files also contain work data. Keep exported files and the `inbox` folder private. Cloud-sync apps and local browsers may retain their own copies, previews or caches.

## Optional desktop AI

AI is used only when you explicitly request a summary and confirm the transfer. The desktop app sends the selected work notes and a summarisation instruction to Anthropic's API using your API key. Anthropic receives the request and applies its own service policies; provider charges may apply. The app does not send the workbook or your invoice configuration for this action.

Review notes before confirming. Remove confidential client material or personal details you do not want to disclose. Do not place API keys in notes, exported files or issue reports.

## Import, backup and removal

Imports require you to select a compatible workbook and approve replacing local data. The selected source is not modified. An existing local workbook is backed up before replacement.

To remove local data, close the app, make any backup you need, and remove its data folder. Remove mirrored files, mobile exports and cloud copies separately, including your provider's trash/version history where applicable. Remove any configured desktop AI key through your operating system's credential manager; the app's credential service is `WorkHoursTracker.Anthropic`. Remove an environment-supplied key from your environment settings as well. Deleting the executable alone does not delete your work records.

## Sharing and support

Use synthetic examples in bug reports. Do not upload the data folder, a real workbook, invoices, screenshots containing financial details, API keys, private paths or unredacted work notes. Check files manually before sharing; a `.gitignore` is a convenience, not a guarantee that a file is safe.
