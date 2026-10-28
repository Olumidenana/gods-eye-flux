"""Clean and deduplicate user profiles CSV before importing into Supabase.

Usage:
    python scripts/clean_profiles_csv.py profiles.csv [clean_profiles.csv]
"""

import csv
import sys
from pathlib import Path


def clean_profiles(input_csv: str, output_csv: str | None = None) -> None:
    inp = Path(input_csv)
    if not inp.exists():
        print(f"Error: file not found: {inp}")
        sys.exit(1)

    out = Path(output_csv) if output_csv else inp.parent / f"{inp.stem}_clean.csv"

    seen_emails: dict[str, dict] = {}
    total_rows = 0

    with open(inp, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            total_rows += 1
            raw_email = (row.get("email") or "").strip().lower()
            if not raw_email or "@" not in raw_email:
                continue

            if raw_email not in seen_emails:
                seen_emails[raw_email] = row
            else:
                existing = seen_emails[raw_email]
                # Merge: prefer real name, earlier created_at, higher visits
                ex_name = (existing.get("name") or "").strip()
                new_name = (row.get("name") or "").strip()
                if not ex_name or ex_name.lower() in ("trader", raw_email.split("@")[0]):
                    if new_name and new_name.lower() not in ("trader", raw_email.split("@")[0]):
                        existing["name"] = new_name

                ex_created = str(existing.get("created_at") or "")
                new_created = str(row.get("created_at") or "")
                if new_created and (not ex_created or new_created < ex_created):
                    existing["created_at"] = new_created

                try:
                    ex_v = int(existing.get("visits") or 0)
                    new_v = int(row.get("visits") or 0)
                    existing["visits"] = max(ex_v, new_v)
                except ValueError:
                    pass

    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(seen_emails.values())

    dupes_removed = total_rows - len(seen_emails)
    print(f"Read {total_rows} total rows.")
    print(f"Deduplicated by email: {len(seen_emails)} unique users.")
    print(f"Removed {dupes_removed} duplicate row(s).")
    print(f"Clean CSV ready at: {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/clean_profiles_csv.py <path_to_profiles.csv> [output_file.csv]")
        sys.exit(1)
    clean_profiles(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
