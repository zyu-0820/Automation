from dataclasses import dataclass
from io import StringIO

import paramiko

from app.config import settings


@dataclass
class SSHConnectionInfo:
    host: str
    port: int
    username: str
    password: str | None = None
    private_key: str | None = None
    become_method: str = ""
    become_user: str | None = None
    become_password: str | None = None


class SSHClient:
    def __init__(self, info: SSHConnectionInfo):
        self._info = info
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None

    @property
    def _use_sudo(self) -> bool:
        return self._info.become_method == "sudo" and bool(self._info.become_password)

    def _wrap_command(self, command: str) -> str:
        if not self._use_sudo:
            return command
        pwd = self._info.become_password.replace("'", "'\\''")
        user = self._info.become_user or "root"
        # Commands with shell metacharacters need sh -c to run entirely under sudo
        needs_shell = any(c in command for c in "|><&;$`")
        if needs_shell:
            escaped = command.replace("\\", "\\\\").replace('"', '\\"')
            return f"echo '{pwd}' | sudo -S -u {user} sh -c \"{escaped}\""
        return f"echo '{pwd}' | sudo -S -u {user} {command}"

    def connect(self):
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = {
            "hostname": self._info.host,
            "port": self._info.port,
            "username": self._info.username,
            "timeout": settings.ssh_connect_timeout,
        }
        if self._info.private_key:
            pkey = paramiko.RSAKey.from_private_key(StringIO(self._info.private_key))
            kwargs["pkey"] = pkey
        elif self._info.password:
            kwargs["password"] = self._info.password

        self._client.connect(**kwargs)
        self._sftp = self._client.open_sftp()

    def test_connection(self) -> tuple[bool, str]:
        try:
            self.connect()
            _, stdout, stderr = self._client.exec_command(
                self._wrap_command("echo ok"), timeout=10
            )
            result = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            self.close()
            if result == "ok":
                return (True, "Connected")
            return (False, err or result or "Unexpected response")
        except Exception as e:
            return (False, str(e))

    def exec_command(self, command: str) -> tuple[int, str, str]:
        if not self._client:
            self.connect()
        wrapped = self._wrap_command(command)
        _, stdout, stderr = self._client.exec_command(
            wrapped, timeout=settings.ssh_operation_timeout
        )
        return 0, stdout.read().decode(), stderr.read().decode()

    def read_file(self, remote_path: str) -> bytes:
        if not self._client:
            self.connect()
        if self._use_sudo:
            _, stdout, stderr = self._client.exec_command(
                self._wrap_command(f"cat {remote_path}"),
                timeout=settings.ssh_operation_timeout,
            )
            err = stderr.read().decode().strip()
            if err and "password" not in err.lower():
                raise FileNotFoundError(err)
            return stdout.read()
        else:
            with self._sftp.open(remote_path, "rb") as f:
                return f.read()

    def write_file(self, remote_path: str, content: bytes) -> None:
        if not self._client:
            self.connect()
        if self._use_sudo:
            import time
            tmp = f"/tmp/jsm_upload_{int(time.time() * 1000000)}"
            with self._sftp.open(tmp, "wb") as f:
                f.write(content)
            self.exec_command(f"mv {tmp} {remote_path}")
            self.exec_command(f"chmod 644 {remote_path}")
        else:
            with self._sftp.open(remote_path, "wb") as f:
                f.write(content)

    def list_dir(self, remote_path: str) -> list[paramiko.SFTPAttributes]:
        if not self._client:
            self.connect()
        try:
            return self._sftp.listdir_attr(remote_path)
        except PermissionError:
            if not self._use_sudo:
                raise
            items = []
            _, stdout, _ = self._client.exec_command(
                self._wrap_command(f"ls -la {remote_path}"),
                timeout=settings.ssh_operation_timeout,
            )
            lines = stdout.read().decode().strip().split("\n")
            for line in lines:
                if line.startswith("total ") or not line.strip():
                    continue
                parts = line.split()
                if len(parts) < 9:
                    continue
                name = " ".join(parts[8:])
                if name in (".", ".."):
                    continue
                perms = parts[0]
                try:
                    size = int(parts[4])
                except ValueError:
                    size = 0
                attr = paramiko.SFTPAttributes()
                attr.filename = name
                attr.st_size = size
                attr.st_mtime = 0
                attr.st_mode = 0o100000  # regular file
                if perms.startswith("d"):
                    attr.st_mode = 0o040000  # directory
                items.append(attr)
            return items

    def stat_file(self, remote_path: str) -> paramiko.SFTPAttributes:
        if not self._client:
            self.connect()
        try:
            return self._sftp.stat(remote_path)
        except PermissionError:
            if not self._use_sudo:
                raise
            attr = paramiko.SFTPAttributes()
            attr.filename = remote_path.split("/")[-1]
            attr.st_size = 0
            attr.st_mtime = 0
            attr.st_mode = 0o100000
            return attr

    def path_exists(self, remote_path: str) -> bool:
        if not self._client:
            self.connect()
        if self._use_sudo:
            _, stdout, _ = self._client.exec_command(
                self._wrap_command(f"test -f {remote_path} || test -d {remote_path} && echo yes || echo no"),
                timeout=settings.ssh_operation_timeout,
            )
            return stdout.read().decode().strip() == "yes"
        try:
            self._sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def rename(self, old_path: str, new_path: str) -> None:
        if not self._client:
            self.connect()
        self.exec_command(f"mv {old_path} {new_path}")

    def close(self):
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
