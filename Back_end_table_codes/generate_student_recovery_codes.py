"""Generate or rotate student recovery codes without storing plaintext in Supabase."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import sys

from api_server import credential_pepper, get_supabase, hash_credential, normalize_index_number


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a backend-only recovery-code hash and a one-time local CSV."
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New CSV path outside the Git repository.",
    )
    parser.add_argument(
        "--index",
        help="Rotate one student's recovery code instead of generating missing codes.",
    )
    return parser.parse_args()


def recovery_fingerprint(code: str) -> str:
    return hmac.new(
        credential_pepper().encode("utf-8"),
        f"recovery:{code}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_unique_code(existing_fingerprints: set[str]) -> tuple[str, str]:
    while True:
        code = "".join(str(secrets.randbelow(10)) for _ in range(16))
        fingerprint = recovery_fingerprint(code)
        if fingerprint not in existing_fingerprints:
            existing_fingerprints.add(fingerprint)
            return code, fingerprint


def format_code(code: str) -> str:
    return "-".join(code[position:position + 4] for position in range(0, 16, 4))


def csv_safe(value: str) -> str:
    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value


def validated_output_path(value: Path) -> tuple[Path, Path]:
    output = value.expanduser().resolve()
    try:
        output.relative_to(REPOSITORY_ROOT)
    except ValueError:
        pass
    else:
        raise ValueError("The recovery-code CSV must be stored outside the Git repository.")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {output}")
    if not output.parent.is_dir():
        raise FileNotFoundError(f"Output directory does not exist: {output.parent}")
    temporary = output.with_name(f"{output.name}.tmp")
    if temporary.exists():
        raise FileExistsError(
            f"A recovery file from an interrupted run already exists: {temporary}"
        )
    return output, temporary


def main() -> int:
    args = parse_args()
    try:
        output, temporary = validated_output_path(args.output)
        database = get_supabase()
        students_response = database.table("students").select("index_number,name").order(
            "index_number"
        ).execute()
        students = students_response.data or []
        credentials_response = database.table("student_credentials").select(
            "index_number,recovery_code_fingerprint,recovery_version"
        ).execute()
        credentials = {
            row["index_number"]: row for row in (credentials_response.data or [])
        }
        existing_fingerprints = {
            row["recovery_code_fingerprint"] for row in credentials.values()
        }

        if args.index:
            target_index = normalize_index_number(args.index)
            students = [row for row in students if row["index_number"] == target_index]
            if not students:
                raise ValueError("The requested student index was not found.")
        else:
            students = [row for row in students if row["index_number"] not in credentials]

        if not students:
            print("No recovery codes need to be generated.")
            return 0

        generated: list[dict[str, str]] = []
        database_rows: list[dict[str, object]] = []
        timestamp = datetime.now(timezone.utc).isoformat()
        for student in students:
            index_number = student["index_number"]
            code, fingerprint = generate_unique_code(existing_fingerprints)
            previous = credentials.get(index_number)
            recovery_version = int(previous["recovery_version"]) + 1 if previous else 1
            generated.append({
                "index_number": csv_safe(index_number),
                "name": csv_safe(student["name"]),
                "recovery_code": format_code(code),
            })
            database_rows.append({
                "index_number": index_number,
                "recovery_code_hash": hash_credential(code),
                "recovery_code_fingerprint": fingerprint,
                "recovery_version": recovery_version,
                "recovery_rotated_at": timestamp,
                "updated_at": timestamp,
            })

        with temporary.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["index_number", "name", "recovery_code"],
            )
            writer.writeheader()
            writer.writerows(generated)
            handle.flush()
            os.fsync(handle.fileno())

        try:
            if args.index:
                database.table("student_password_challenges").delete().eq(
                    "index_number", normalize_index_number(args.index)
                ).execute()
            database.table("student_credentials").upsert(
                database_rows,
                on_conflict="index_number",
                default_to_null=False,
            ).execute()
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

        temporary.replace(output)
        print(f"Generated {len(generated)} recovery code(s) in: {output}")
        print("Keep this CSV offline. The application and database cannot recover these codes.")
        return 0
    except Exception as error:
        print(f"Recovery-code generation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
