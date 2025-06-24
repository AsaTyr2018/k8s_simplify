import shutil


def check_local_tools(use_password: bool) -> None:
    """Ensure required executables exist on the host system."""
    needed = ["ssh"]
    if use_password:
        needed.append("sshpass")
    missing = [tool for tool in needed if shutil.which(tool) is None]
    if missing:
        tools = ", ".join(missing)
        raise RuntimeError(f"Missing required local tools: {tools}")
