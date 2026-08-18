# Security Policy

## Reporting a Security Issue

Please do not publicly disclose security vulnerabilities before they have been reviewed.

If you identify a security issue involving SkyTrack, open a private security report through GitHub when available.

## Never Commit Secrets

Do not commit:

* API keys
* Passwords
* Service-account credentials
* Private keys
* `.env` files
* OAuth credentials
* Access tokens

Use environment variables or Streamlit Secrets for sensitive configuration.

## Google Sheets Credentials

Google service-account credentials should never be committed to the repository.

If credentials are accidentally exposed, revoke and rotate them immediately.

## Responsible Disclosure

Security reports are appreciated and will be reviewed as quickly as reasonably possible.
