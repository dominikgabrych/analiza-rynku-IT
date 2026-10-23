# ADR 0008: Backups with pg_dump and an age-encrypted off-site copy

- Status: accepted
- Date: 2026-10-23

## Context

The presence history of postings cannot be fetched again, and the machine has one disk. The database volume lives inside Docker's disk image, so a Docker reset deletes it. Only an encrypted copy may leave the machine, and nothing that can decrypt it may stay there.

## Decision

- `pg_dump` runs after each ingestion run that passed its checks. The copies are kept outside Docker, and the 3 newest stay (counted as copies, not days).
- `radar migrate` makes a backup before applying migrations and keeps it.
- Once a week the newest copy is encrypted with [age](https://age-encryption.org/) to a public key and synced to cloud storage. The private key lives only in a password manager.

## Alternatives considered

- **Copying the volume files:** inconsistent while the server runs.
- **pgBackRest or WAL-G:** point-in-time recovery that this data does not need, since it changes once a day.
- **Daily and weekly generations:** more copies do not catch silent errors; checks after each run and repair by run id do.
- **Encryption with a passphrase:** an unattended run would need the passphrase on disk.
- **gpg:** the same model, but its keyring and key export add ways to lose the key; age keys are one line each.

## Consequences

- A disk failure loses at most a week of data; the local copies cover everything else.
- Losing the private key makes the off-site copy useless.
- age has to be installed wherever backups are made or restored.
