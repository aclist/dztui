import shlex


def concat_bash_args(command: str) -> list[str]:
    return shlex.split(command)
