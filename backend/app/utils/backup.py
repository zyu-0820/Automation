from datetime import date


def generate_backup_name(original_path: str) -> str:
    today = date.today().strftime("%Y%m%d")
    return f"{original_path}.bak-{today}"


def generate_backup_name_with_seq(original_path: str, existing_names: list[str]) -> str:
    base = generate_backup_name(original_path)
    if base not in existing_names:
        return base
    seq = 1
    while True:
        candidate = f"{base}.{seq}"
        if candidate not in existing_names:
            return candidate
        seq += 1
