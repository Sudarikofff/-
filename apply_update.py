"""Install reviewed code changes while leaving the target database untouched."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def apply(source, target):
    manifest = json.loads((source / "update-manifest.json").read_text())
    source = source.resolve()
    target = target.resolve()
    if source == target:
        raise ValueError("Укажите папку назначения, отличную от папки с программой.")
    if not (target / "main.py").is_file():
        raise ValueError("В папке назначения не найден main.py.")

    files = manifest["files"]
    for name, info in files.items():
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("Недопустимый путь в манифесте.")
        if digest(source / name) != info["new_sha256"]:
            raise ValueError(f"Файл в папке программы изменился: {name}")
        destination = target / name
        if destination.is_symlink() or not destination.resolve().is_relative_to(target):
            raise ValueError(f"Недопустимая символическая ссылка: {name}")
        if digest(destination) not in (info["old_sha256"], info["new_sha256"]):
            raise ValueError(f"Файл в папке назначения изменился: {name}")

    pending = [name for name, info in files.items()
               if digest(target / name) != info["new_sha256"]]
    if not pending:
        print("Обновление не требуется.")
        return

    backup = target / "backup" / ("code-update-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    backup.mkdir(parents=True)
    replaced = []
    try:
        for name in pending:
            destination = target / name
            if destination.exists():
                saved = backup / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, saved)
        for name in pending:
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False,
                                             prefix=".profile-update-") as handle:
                staging = Path(handle.name)
            try:
                shutil.copy2(source / name, staging)
                if digest(destination) not in (files[name]["old_sha256"], files[name]["new_sha256"]):
                    raise ValueError(f"Файл в папке назначения изменился: {name}")
                staging.replace(destination)
                replaced.append(name)
            finally:
                staging.unlink(missing_ok=True)
    except Exception:
        for name in reversed(replaced):
            destination = target / name
            saved = backup / name
            if saved.exists():
                shutil.copy2(saved, destination)
            else:
                destination.unlink(missing_ok=True)
        raise
    print(f"Обновлено файлов: {len(pending)}. Копия исходных файлов: {backup}")
    print("База данных не заменялась.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Перенос файлов программы в другую папку.")
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    try:
        apply(Path(__file__).resolve().parent, args.project)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
