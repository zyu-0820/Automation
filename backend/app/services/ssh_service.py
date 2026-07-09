"""
SSH 服务模块 - 提供对远程服务器的各类操作

本模块封装了通过 SSH 协议对远程服务器执行的常见操作,包括:
- SSH 连接测试
- 服务扫描与状态检测
- 服务启停控制
- 配置文件读取/写入
- JAR 包上传/删除

所有 SSH 操作均为同步阻塞 I/O,为了不阻塞 FastAPI 事件循环,
统一使用 run_in_executor 将其放到线程池中执行。
"""

import asyncio
import logging

import yaml

logger = logging.getLogger("ssh_service")

from app.models.server import Server
from app.schemas.server import ServerWithCredentials
from app.utils.backup import find_unique_backup_name
from app.utils.encryption import decrypt
from app.utils.ssh_client import SSHClient, SSHConnectionInfo


def _validate_yaml(content: str) -> None:
    """
    校验 YAML 内容是否合法

    Args:
        content: YAML 格式的字符串内容

    Raises:
        yaml.YAMLError: 当 YAML 语法错误时抛出

    Notes:
        - 使用 SafeLoader 防止任意代码执行
        - 通过 add_multi_constructor 忽略自定义标签(如 Spring 的 !AUTHORITY)
    """
    loader = yaml.SafeLoader
    loader.add_multi_constructor("", lambda loader, suffix, node: None)
    yaml.load(content, Loader=loader)


def _service_dir(server: Server, service_name: str, custom_path: str | None = None) -> str:
    """
    计算服务的完整目录路径

    Args:
        server: 服务器对象,包含 service_base_path 配置
        service_name: 服务名称
        custom_path: 自定义路径(可选),优先于默认路径

    Returns:
        服务目录的绝对路径,末尾不带斜杠
        格式: /home/apps/services/service-name 或 custom-path

    Examples:
        _service_dir(server, "myapp") -> "/home/apps/services/myapp"
        _service_dir(server, "myapp", "/opt/myapp") -> "/opt/myapp"
    """
    if custom_path:
        return custom_path.rstrip("/")
    return f"{server.service_base_path.rstrip('/')}/{service_name}"


def _parse_extensions(ext_str: str) -> tuple[str, ...]:
    """
    解析配置文件扩展名列表

    Args:
        ext_str: 逗号分隔的扩展名字符串,如 "yml,yaml,xml"

    Returns:
        标准化后的扩展名元组,每个扩展名以点开头
        默认值: (".yml", ".yaml", ".xml")

    Examples:
        _parse_extensions("yml,yaml,xml") -> (".yml", ".yaml", ".xml")
        _parse_extensions(".yml, .yaml") -> (".yml", ".yaml")
    """
    exts = [e.strip().lstrip(".") for e in ext_str.split(",") if e.strip()]
    return tuple(f".{e}" for e in exts) if exts else (".yml", ".yaml", ".xml")


def _build_ssh_info(server: ServerWithCredentials) -> SSHConnectionInfo:
    """
    根据服务器凭证构建 SSH 连接信息

    Args:
        server: 包含解密后凭证的服务器对象

    Returns:
        SSHConnectionInfo 对象,包含连接所需的全部信息

    Notes:
        - 根据 auth_type 决定使用密码还是私钥认证
        - become_* 用于权限提升(sudo/su)
    """
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
    """
    从数据库模型中解密并构建包含凭证的服务器对象

    Args:
        server: 从数据库读取的 Server 模型对象(加密字段未解密)

    Returns:
        ServerWithCredentials 对象,包含解密后的密码/私钥

    Notes:
        - 加密字段在数据库中以密文存储
        - 调用此函数前需确保已初始化加密密钥
    """
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
    """
    SSH 远程操作服务类

    提供静态方法封装对远程服务器的各类操作。
    所有方法均为异步,但 SSH 底层为同步 I/O,
    因此内部使用 run_in_executor 在线程池中执行。
    """

    @staticmethod
    async def test_connection(server: Server) -> tuple[bool, str]:
        """
        测试 SSH 连接是否可用

        Args:
            server: 服务器对象

        Returns:
            (成功标志, 消息) 元组
            成功时: (True, "Connection successful")
            失败时: (False, 错误原因)
        """
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, ssh.test_connection)

    @staticmethod
    async def scan_services(server: Server) -> list[str]:
        """
        扫描服务器服务基础目录,发现所有服务

        Args:
            server: 服务器对象

        Returns:
            服务名称列表(目录名)
            仅返回子目录,不含文件

        Notes:
            - 扫描 server.service_base_path 下的所有子目录
            - 使用 st_mode 的目录标志位(0o40000)过滤
        """
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
        """
        获取服务的运行状态

        Args:
            server: 服务器对象
            service_name: 服务名称

        Returns:
            服务状态字符串:
            - "running": 服务正在运行
            - "stopped": 服务已停止
            - "unknown": 无法确定状态(连接错误等)

        Detection Logic:
            1. 优先使用 systemctl is-active 命令
            2. 回退方案: 使用 ps 命令配合路径正则匹配
               正则 /service-name/ 或 /service-name$ 避免前缀冲突
               (如 es-data-sync 不会匹配 es-data-sync-1)
        """
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        host = server.host

        def _check():
            ssh.connect()
            try:
                # 1) 优先使用 systemctl 检测 systemd 服务
                cmd1 = f"systemctl is-active {service_name} 2>/dev/null"
                logger.info("[%s] cmd: %s", host, cmd1)
                _, out, _ = ssh.exec_command(cmd1)
                out = out.strip()
                logger.info("[%s] systemctl output: %r", host, out)
                if out == "active":
                    return "running"

                # 2) 回退方案: 通过进程列表和路径匹配检测
                # 正则 /service-name/ 或 /service-name$ 避免前缀冲突
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
        """
        服务控制的核心实现(start/stop/restart 复用此方法)

        Args:
            server: 服务器对象
            service_name: 服务名称
            action: 操作类型 ("start", "stop", "restart")
            custom_path: 服务自定义路径
            control_method: 控制方式
                - "auto": 自动选择(优先 systemd, 回退脚本)
                - "systemd": 仅使用 systemctl
                - "script": 仅使用 bin/start.sh 等脚本

        Returns:
            (成功标志, 消息) 元组

        Control Logic:
            1. 尝试 systemctl 命令
               - 如果返回 "not-found" 或 "Failed" 则认为失败
            2. 回退方案: 查找 bin/start.sh 或 script/start.sh 脚本执行
        """
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        svc_dir = _service_dir(server, service_name, custom_path)

        def _exec():
            ssh.connect()
            try:
                # 方案1: 尝试 systemctl
                if control_method in ("auto", "systemd"):
                    _, out, err = ssh.exec_command(
                        f"systemctl {action} {service_name} 2>&1"
                    )
                    err = err.strip()
                    out = out.strip()
                    # 检查 systemctl 是否成功执行(不包含错误标识)
                    if "not-found" not in err and "not loaded" not in err and "Failed" not in err and "Unit" not in err:
                        return True, out or err or f"systemctl {action} succeeded"
                    # 强制使用 systemd 模式时,失败直接返回
                    if control_method == "systemd":
                        return False, f"systemctl {action} failed: {err}"

                # 方案2: 回退到脚本方式
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
    async def start_service(
        server: Server, service_name: str, custom_path: str | None = None, control_method: str = "auto"
    ) -> tuple[bool, str]:
        """
        启动指定服务

        Args:
            server: 服务器对象
            service_name: 服务名称
            custom_path: 服务自定义路径
            control_method: 控制方式

        Returns:
            (成功标志, 消息) 元组
        """
        return await SSHService._service_control(server, service_name, "start", custom_path, control_method)

    @staticmethod
    async def stop_service(
        server: Server, service_name: str, custom_path: str | None = None, control_method: str = "auto"
    ) -> tuple[bool, str]:
        """
        停止指定服务

        Args:
            server: 服务器对象
            service_name: 服务名称
            custom_path: 服务自定义路径
            control_method: 控制方式

        Returns:
            (成功标志, 消息) 元组
        """
        return await SSHService._service_control(server, service_name, "stop", custom_path, control_method)

    @staticmethod
    async def restart_service(
        server: Server, service_name: str, custom_path: str | None = None, control_method: str = "auto"
    ) -> tuple[bool, str]:
        """
        重启指定服务

        Args:
            server: 服务器对象
            service_name: 服务名称
            custom_path: 服务自定义路径
            control_method: 控制方式

        Returns:
            (成功标志, 消息) 元组
        """
        return await SSHService._service_control(server, service_name, "restart", custom_path, control_method)

    @staticmethod
    async def list_config_files(
        server: Server, service_name: str, custom_path: str | None = None, extensions: str | None = None
    ) -> list[dict]:
        """
        列出服务目录下的配置文件

        Args:
            server: 服务器对象
            service_name: 服务名称
            custom_path: 服务自定义路径
            extensions: 额外的扩展名过滤(可选),默认使用 server.config_extensions

        Returns:
            文件信息列表,每个元素包含:
            - name: 文件名
            - dir: 所在目录 ("conf" 或 "config")
            - size: 文件大小(字节)
            - modified_at: 修改时间戳

        Notes:
            - 扫描 conf/ 和 config/ 两个目录
            - 仅返回符合扩展名的文件
        """
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
                        # 目录不存在时跳过
                        continue
                    for a in attrs:
                        if not a.st_mode:
                            continue
                        is_dir = bool(a.st_mode & 0o40000)
                        # 跳过目录和非配置文件
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
        """
        解析配置文件的实际路径

        Args:
            server: 服务器对象
            service_name: 服务名称
            filename: 文件名

        Returns:
            配置文件的完整路径

        Notes:
            依次检查 conf/ 和 config/ 目录,返回第一个存在的路径
        """
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
    async def read_config_file(
        server: Server, service_name: str, filename: str, dir: str = "conf", custom_path: str | None = None
    ) -> str:
        """
        读取远程配置文件内容

        Args:
            server: 服务器对象
            service_name: 服务名称
            filename: 文件名
            dir: 配置文件目录,默认 "conf"
            custom_path: 服务自定义路径

        Returns:
            文件内容(UTF-8 字符串)
        """
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
    ) -> tuple[str, str | None]:
        """
        写入远程配置文件

        Args:
            server: 服务器对象
            service_name: 服务名称
            filename: 文件名
            content: 新的文件内容
            dir: 配置文件目录,默认 "conf"
            custom_path: 服务自定义路径

        Returns:
            (文件路径, 备份路径或None) 元组

        Safety Features:
            - YAML 文件写入前自动校验语法
            - 原文件存在时自动备份为 .bak-YYYYMMDD
            - 备份操作在写入前完成,确保数据安全
        """
        # YAML 语法校验
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
                # 如果原文件存在,先备份
                if ssh.path_exists(remote_path):
                    bak = find_unique_backup_name(lambda p: ssh.path_exists(p), remote_path)
                    ssh.rename(remote_path, bak)
                # 写入新内容
                ssh.write_file(remote_path, content.encode("utf-8"))
                return bak
            finally:
                ssh.close()

        backup_path = await loop.run_in_executor(None, _write)
        return remote_path, backup_path

    @staticmethod
    async def append_config_file(
        server: Server, service_name: str, filename: str, content: str, dir: str = "conf", custom_path: str | None = None
    ) -> tuple[str, str | None]:
        if filename.endswith((".yml", ".yaml")):
            _validate_yaml(content)
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        svc_dir = _service_dir(server, service_name, custom_path)
        remote_path = f"{svc_dir}/{dir}/{filename}"

        def _append():
            bak = None
            ssh.connect()
            try:
                if ssh.path_exists(remote_path):
                    bak = find_unique_backup_name(lambda p: ssh.path_exists(p), remote_path)
                    ssh.exec_command(f"cp -p {remote_path} {bak}")
                ssh.append_file(remote_path, content.encode("utf-8"))
                return bak
            finally:
                ssh.close()

        backup_path = await loop.run_in_executor(None, _append)
        return remote_path, backup_path

    @staticmethod
    async def list_jars(server: Server, service_name: str, custom_path: str | None = None) -> list[dict]:
        """
        列出服务 lib 目录下的所有 JAR 文件

        Args:
            server: 服务器对象
            service_name: 服务名称
            custom_path: 服务自定义路径

        Returns:
            JAR 文件信息列表,每个元素包含:
            - name: 文件名
            - size: 文件大小(字节)
            - modified_at: 修改时间戳
        """
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
    ) -> tuple[str, str | None]:
        """
        上传 JAR 文件到远程服务器

        Args:
            server: 服务器对象
            service_name: 服务名称
            filename: 文件名
            content: 文件内容(二进制)
            custom_path: 服务自定义路径

        Returns:
            (文件路径, 备份路径或None) 元组

        Safety Features:
            - 原文件存在时自动备份为 .bak-YYYYMMDD
        """
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
                    bak = find_unique_backup_name(lambda p: ssh.path_exists(p), remote_path)
                    ssh.rename(remote_path, bak)
                ssh.write_file(remote_path, content)
                return bak
            finally:
                ssh.close()

        backup_path = await loop.run_in_executor(None, _upload)
        return remote_path, backup_path

    @staticmethod
    async def delete_jar(server: Server, service_name: str, filename: str, custom_path: str | None = None) -> None:
        """
        删除远程服务器上的 JAR 文件

        Args:
            server: 服务器对象
            service_name: 服务名称
            filename: 文件名
            custom_path: 服务自定义路径

        Safety Features:
            - 不直接删除文件,而是重命名为 .deleted-YYYYMMDD
            - 保留删除历史,便于恢复
        """
        creds = _server_with_creds(server)
        ssh = SSHClient(_build_ssh_info(creds))
        loop = asyncio.get_event_loop()
        svc_dir = _service_dir(server, service_name, custom_path)
        remote_path = f"{svc_dir}/lib/{filename}"

        def _delete():
            ssh.connect()
            try:
                if ssh.path_exists(remote_path):
                    bak = find_unique_backup_name(lambda p: ssh.path_exists(p), remote_path, marker="deleted")
                    ssh.rename(remote_path, bak)
            finally:
                ssh.close()

        await loop.run_in_executor(None, _delete)
