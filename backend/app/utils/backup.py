from datetime import date


def generate_backup_name(original_path: str) -> str:
    """生成基于日期的备份文件名，如 config.properties.bak-20260709"""
    today = date.today().strftime("%Y%m%d")
    return f"{original_path}.bak-{today}"


def generate_backup_name_with_seq(original_path: str, existing_names: list[str]) -> str:
    """生成带序号的备份名，用于本地已有文件列表的去重"""
    base = generate_backup_name(original_path)
    if base not in existing_names:
        return base
    seq = 1
    while True:
        candidate = f"{base}.{seq}"
        if candidate not in existing_names:
            return candidate
        seq += 1


def find_unique_backup_name(path_exists_checker, remote_path: str, marker: str = "bak") -> str:
    """
    在远程服务器上查找唯一的备份文件名。

    通过回调 path_exists_checker(name) 检查远程文件是否存在，
    自动追加 .1 .2 .3 序号直到找到不冲突的名称。

    Args:
        path_exists_checker: 可调用对象，接收文件路径返回 bool
        remote_path: 原始文件路径
        marker: 备份标记，默认为 "bak"（生成 .bak-YYYYMMDD），
                传入 "deleted" 则生成 .deleted-YYYYMMDD

    Returns:
        唯一的备份文件路径
    """
    today = date.today().strftime("%Y%m%d")
    base = f"{remote_path}.{marker}-{today}"
    if not path_exists_checker(base):
        return base
    seq = 1
    while True:
        candidate = f"{base}.{seq}"
        if not path_exists_checker(candidate):
            return candidate
        seq += 1
