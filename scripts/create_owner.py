"""Create a business and its owner login.

Usage: PYTHONPATH=. python scripts/create_owner.py --db app.db --slug barbearia --name "Barbearia" --email dono@x.com
The password is read from a hidden prompt, never from the command line.
"""

import argparse
import getpass

from adapters.argon_hasher import ArgonHasher
from adapters.sqlite_auth import SqliteOwners
from adapters.sqlite_catalog import SqliteCatalog
from adapters.sqlite_db import Database
from domain.auth import is_valid_email, is_valid_password, normalize_email
from domain.public import is_valid_slug


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    slug = slug.strip().lower()
    if not is_valid_slug(slug):
        print("slug must have 3-40 lowercase letters, digits or hyphens (no hyphens at ends)")
        return 1
    email = normalize_email(args.email)
    if not is_valid_email(email):
        print("invalid e-mail")
        return 1
    password = getpass.getpass("Password (8-128 chars): ")
    if not is_valid_password(password):
        print("password must have 8 to 128 characters")
        return 1
    db = Database(args.db)
    db.migrate()
    catalog = SqliteCatalog(db)
    business = catalog.business_by_slug(slug) or catalog.add_business(slug, args.name)
    SqliteOwners(db).add_owner(business.id, email, ArgonHasher().hash(password))
    print(f"owner {email} created for business {business.slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
