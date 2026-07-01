import asyncio
import logging

import yaml

logger = logging.getLogger("ssh_service")

from app.models.server import Server
from app.schemas.server import ServerWithCredentials
from app.utils.encryption import decrypt
from app.utils.ssh_client import SSHClient, SSHConnectionInfo


def _validate_yaml(content: str) -> None:
    """Validate YAML content, ignoring custom tags like !AUTHORITY."""
    loader = yaml.SafeLoader
    loader.add_multi_constructor("", lambda loader, suffix, node: None)
    yaml.load(content, Loader=loader)


def _service_dir(server: Server, service_name: str, custom_path: str | None = None) -> str:
    if custom_path:
        return custom_path.rstrip("/")
    return f"{server.service_base_path.rstrip('/')}/{service_name}"


def _parse_extensions(ext_str: str) -> tuple[str, ...]:
    exts = [e.strip().lstrip(".") for e in ext_str.split(",") if e.strip()]
    return tuple(f".{e}" for e in exts) if exts else (".yml", ".yaml", ".xml")


def _build_ssh_info(server: ServerWithCredentials) -> SSHConnectionInfo:
    return SSHConnectionInfo(
        host=server.host,
        port=server.port,
        username=server.username,
        password=server.password if server.auth_type == "password" else None,
        private_key=server.private_key if server.auth_type == "key" else None,
        become_method=server.become_method,
        become_user=server.become_user,
        become_password=server.become_password,
    )


def _server_with_creds(server: Server) -> ServerWithCredentials:
    d = ServerWithCredentials(
        id=server.id,
        name=server.name,
        host=server.host,
        port=server.port,
        username=server.username,
        auth_type=server.auth_type,
        become_method=server.become_method or "",
        become_user=server.become_user,
        service_base_path=server.service_base_path,
        created_at=server.created_at,
        updated_at=server.updated_at,
    )
    if server.encrypted_password:
        d.password = decrypt(server.encrypted_password)
    if server.encrypted_private_key:
        d.private_key = decrypt(server.encrypted_private_key)
    if server.encrypted_become_password:
        d.become_password = decrypt(server.encrypted_become_password)
    return d


class SSHService:

    @staticmethod
    async def test_connection(server: Server) -> tuple[bool, str]:
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, ssh.test_connection)

    @staticmethod
    async def scan_services(server: Server) -> list[str]:
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()

        def _scan():
            ssh.connect()
            try:
                base = server.service_base_path.rstrip("/")
                attrs = ssh.list_dir(base)
                return [
                    a.filename
                    for a in attrs
                    if a.st_mode is not None and (a.st_mode & 0o40000)
                ]
            finally:
                ssh.close()

        try:
            return await loop.run_in_executor(None, _scan)
        except Exception:
            return []

    @staticmethod
    async def get_service_status(server: Server, service_name: str) -> str:
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        host = server.host

        def _check():
            ssh.connect()
            try:
                # 1) try systemctl
                cmd1 = f"systemctl is-active {service_name} 2>/dev/null"
                logger.info("[%s] cmd: %s", host, cmd1)
                _, out, _ = ssh.exec_command(cmd1)
                out = out.strip()
                logger.info("[%s] systemctl output: %r", host, out)
                if out == "active":
                    return "running"

                # 2) path-based match: /service_name/ or /service_name at end of line
                # This avoids prefix collisions: es-data-sync won't match es-data-sync-1
                cmd2 = f"sh -c \"ps -ef | grep -E '/({service_name})(/|\$)' | grep -v grep\""
                logger.info("[%s] cmd: %s", host, cmd2)
                _, out, _ = ssh.exec_command(cmd2)
                logger.info("[%s] path-grep output (%d chars): %r", host, len(out), out[:500])
                if out.strip():
                    return "running"
                return "stopped"
            except Exception as e:
                logger.error("[%s] %s: error: %s", host, service_name, e)
                return "unknown"
            finally:
                ssh.close()

        return await loop.run_in_executor(None, _check)

    @staticmethod
    async def _service_control(
        server: Server, service_name: str, action: str, custom_path: str | None = None, control_method: str = "auto"
    ) -> tuple[bool, str]:
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        svc_dir = _service_dir(server, service_name, custom_path)

        def _exec():
            ssh.connect()
            try:
                if control_method in ("auto", "systemd"):
                    _, out, err = ssh.exec_command(
                        f"systemctl {action} {service_name} 2>&1"
                    )
                    err = err.strip()
                    out = out.strip()
                    if "not-found" not in err and "not loaded" not in err and "Failed" not in err and "Unit" not in err:
                        return True, out or err or f"systemctl {action} succeeded"
                    if control_method == "systemd":
                        return False, f"systemctl {action} failed: {err}"

                if control_method in ("auto", "script"):
                    for d in ("bin", "script"):
                        script_path = f"{svc_dir}/{d}/{action}.sh"
                        _, script_out, script_err = ssh.exec_command(
                            f"test -x {script_path} && {script_path} 2>&1 || echo NOT_FOUND"
                        )
                        result = script_out.strip() + " " + script_err.strip()
                        if "NOT_FOUND" not in result:
                            return True, result.strip() or f"{action} executed via {script_path}"
                    return False, f"No {action}.sh found in bin/ or script/"

                return False, "Unknown control method"
            except Exception as e:
                return False, str(e)
            finally:
                ssh.close()

        return await loop.run_in_executor(None, _exec)

    @staticmethod
    async def start_service(server: Server, service_name: str, custom_path: str | None = None, control_method: str = "auto") -> tuple[bool, str]:
        return await SSHService._service_control(server, service_name, "start", custom_path, control_method)

    @staticmethod
    async def stop_service(server: Server, service_name: str, custom_path: str | None = None, control_method: str = "auto") -> tuple[bool, str]:
        return await SSHService._service_control(server, service_name, "stop", custom_path, control_method)

    @staticmethod
    async def restart_service(server: Server, service_name: str, custom_path: str | None = None, control_method: str = "auto") -> tuple[bool, str]:
        return await SSHService._service_control(server, service_name, "restart", custom_path, control_method)

    @staticmethod
    async def list_config_files(server: Server, service_name: str, custom_path: str | None = None, extensions: str | None = None) -> list[dict]:
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        ext_str = extensions or server.config_extensions or "yml,yaml,xml"
        valid_ext = _parse_extensions(ext_str)
        candidate_dirs = ("conf", "config")
        svc_dir = _service_dir(server, service_name, custom_path)

        def _list():
            ssh.connect()
            try:
                files = []
                for dir_name in candidate_dirs:
                    conf_dir = f"{svc_dir}/{dir_name}"
                    try:
                        attrs = ssh.list_dir(conf_dir)
                    except Exception:
                        continue
                    for a in attrs:
                        if not a.st_mode:
                            continue
                        is_dir = bool(a.st_mode & 0o40000)
                        if is_dir or not a.filename.endswith(valid_ext):
                            continue
                        stat = ssh.stat_file(f"{conf_dir}/{a.filename}")
                        files.append({
                            "name": a.filename,
                            "dir": dir_name,
                            "size": stat.st_size,
                            "modified_at": str(stat.st_mtime),
                        })
                return files
            except Exception:
                return []
            finally:
                ssh.close()

        return await loop.run_in_executor(None, _list)

    @staticmethod
    async def _resolve_config_path(server: Server, service_name: str, filename: str) -> str:
        base = server.service_base_path.rstrip("/")
        for d in ("conf", "config"):
            path = f"{base}/{service_name}/{d}/{filename}"
            creds = _server_with_creds(server)
            ssh = SSHClient(_build_ssh_info(creds))
            loop = asyncio.get_event_loop()

            def _check():
                ssh.connect()
                try:
                    exists = ssh.path_exists(path)
                finally:
                    ssh.close()
                return exists

            if await loop.run_in_executor(None, _check):
                return path
        return f"{base}/{service_name}/conf/{filename}"

    @staticmethod
    async def read_config_file(server: Server, service_name: str, filename: str, dir: str = "conf", custom_path: str | None = None) -> str:
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        svc_dir = _service_dir(server, service_name, custom_path)
        remote_path = f"{svc_dir}/{dir}/{filename}"

        def _read():
            ssh.connect()
            try:
                return ssh.read_file(remote_path).decode("utf-8")
            finally:
                ssh.close()

        content = await loop.run_in_executor(None, _read)
        return content

    @staticmethod
    async def write_config_file(
        server: Server, service_name: str, filename: str, content: str, dir: str = "conf", custom_path: str | None = None
    ) -> str:
        if filename.endswith((".yml", ".yaml")):
            _validate_yaml(content)
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        svc_dir = _service_dir(server, service_name, custom_path)
        remote_path = f"{svc_dir}/{dir}/{filename}"

        def _write():
            bak = None
            ssh.connect()
            try:
                if ssh.path_exists(remote_path):
                    from datetime import date

                    today = date.today().strftime("%Y%m%d")
                    bak = f"{remote_path}.bak-{today}"
                    ssh.rename(remote_path, bak)
                ssh.write_file(remote_path, content.encode("utf-8"))
                return bak
            finally:
                ssh.close()

        backup_path = await loop.run_in_executor(None, _write)
        return remote_path, backup_path

    @staticmethod
    async def list_jars(server: Server, service_name: str, custom_path: str | None = None) -> list[dict]:
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        svc_dir = _service_dir(server, service_name, custom_path)

        def _list():
            ssh.connect()
            try:
                lib_dir = f"{svc_dir}/lib"
                attrs = ssh.list_dir(lib_dir)
                files = []
                for a in attrs:
                    if not a.st_mode:
                        continue
                    is_dir = bool(a.st_mode & 0o40000)
                    if is_dir or not a.filename.endswith(".jar"):
                        continue
                    stat = ssh.stat_file(f"{lib_dir}/{a.filename}")
                    files.append({
                        "name": a.filename,
                        "size": stat.st_size,
                        "modified_at": str(stat.st_mtime),
                    })
                return files
            except Exception:
                return []
            finally:
                ssh.close()

        return await loop.run_in_executor(None, _list)

    @staticmethod
    async def upload_jar(
        server: Server, service_name: str, filename: str, content: bytes, custom_path: str | None = None
    ) -> str:
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        svc_dir = _service_dir(server, service_name, custom_path)
        remote_path = f"{svc_dir}/lib/{filename}"

        def _upload():
            bak = None
            ssh.connect()
            try:
                if ssh.path_exists(remote_path):
                    from datetime import date

                    today = date.today().strftime("%Y%m%d")
                    bak = f"{remote_path}.bak-{today}"
                    ssh.rename(remote_path, bak)
                ssh.write_file(remote_path, content)
                return bak
            finally:
                ssh.close()

        backup_path = await loop.run_in_executor(None, _upload)
        return remote_path, backup_path

    @staticmethod
    async def delete_jar(server: Server, service_name: str, filename: str, custom_path: str | None = None) -> None:
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        svc_dir = _service_dir(server, service_name, custom_path)
        remote_path = f"{svc_dir}/lib/{filename}"

        def _delete():
            ssh.connect()
            try:
                if ssh.path_exists(remote_path):
                    from datetime import date

                    today = date.today().strftime("%Y%m%d")
                    ssh.rename(remote_path, f"{remote_path}.deleted-{today}")
            finally:
                ssh.close()

        await loop.run_in_executor(None, _delete)
