"""Create or update a teacher account in the local credentials file."""

import getpass
import hashlib
import json
import os
import secrets

from app import PASSWORD_HASH_ITERATIONS, TEACHER_CREDENTIALS_FILE


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username:
        raise SystemExit("Username cannot be empty.")

    password = getpass.getpass("Teacher password (minimum 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    try:
        credentials = json.loads(TEACHER_CREDENTIALS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        credentials = {"teachers": []}

    if not isinstance(credentials, dict) or not isinstance(
        credentials.get("teachers"), list
    ):
        raise SystemExit("Teacher credentials file has an invalid structure.")

    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    teacher = {"username": username, "salt": salt, "password_hash": password_hash}
    teachers = credentials["teachers"]
    for index, existing in enumerate(teachers):
        if isinstance(existing, dict) and existing.get("username") == username:
            teachers[index] = teacher
            break
    else:
        teachers.append(teacher)

    TEACHER_CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEACHER_CREDENTIALS_FILE.write_text(
        json.dumps({"teachers": teachers}, indent=2) + "\n", encoding="utf-8"
    )
    os.chmod(TEACHER_CREDENTIALS_FILE, 0o600)
    print(f"Teacher account saved to {TEACHER_CREDENTIALS_FILE}.")


if __name__ == "__main__":
    main()
