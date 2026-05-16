# Security

## Secrets

This project reads API credentials from local environment variables through
`.env`. Never commit:

- `.env` or other local env files
- X bearer tokens or OAuth client secrets
- OpenAI API keys
- `xurl` token stores or command output that includes credentials
- generated private content, local SQLite databases, or cache directories

Use `.env.example` for placeholders only.

## Reporting

If you find a security issue, do not open a public issue with secrets or exploit
details. Contact the repository owner privately, then share a minimal sanitized
reproduction once a fix path is agreed.
