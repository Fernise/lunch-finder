# Security policy

## Reporting

Report potential vulnerabilities privately using [GitHub private vulnerability reporting](https://github.com/Fernise/lunch-finder/security/advisories/new). Include the affected commit, impact and reproduction steps using fictional data. Do not post credentials, private records or exploit details in public issues.

## Development boundaries

- Populate credentials only in ignored local configuration or the deployment provider’s secret store.
- Use independent development accounts, fictional fixtures and disposable local databases.
- Keep customer, learner, identity, account, order and notification data outside Git.
- Review staged files and history; `.gitignore` does not remove already tracked secrets.
- Rotate a credential at its issuing provider if it is exposed. Removing a file is not revocation.

The repository includes a Gitleaks history scan and a tracked-file publication policy check in CI. These are safeguards, not proof that software is vulnerability-free. External integrations and deployment hardening need their own verification. See `docs/CONFIGURATION.md` for project-specific requirements.
