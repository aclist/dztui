from datetime import datetime

def get_time() -> int:
    return int(datetime.now().timestamp())

# TODO: deprecated
#def write_time(path: Path) -> None:
#    time = get_time()
#    Path.write_text(str(time))

def is_elapsed(time_before: int) -> bool:
    time_now = get_time()
    if time_now - time_before <= 30:
        return False
    else:
        return True
