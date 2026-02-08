from pathlib import Path
import os
import shutil
import docker


def copy_files(src_dir: Path, pattern: str, dest_root: Path, move: bool = True):
    for src_path in src_dir.glob(pattern):
        dest_path = dest_root / src_path.relative_to(src_dir.parent)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if move:
            src_path.replace(dest_path)
        if src_path.is_file():
            shutil.copy2(src_path, dest_path)
        elif src_path.is_dir():
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)


def build_assessments(in_path, build_path):
    client = docker.from_env()

    for file in os.listdir(in_path):
        if file.endswith(".md"):
            metadata_file = Path(file).with_suffix(".yml")
            client.containers.run(
                image="ghcr.io/re3-work/pandoc-assessments:latest",
                auto_remove=True,
                detach=False,
                volumes=[f"{in_path.absolute()}:/data/"],
                command=[file, "-d", metadata_file.as_posix()],
            )
    copy_files(in_path, "*.pdf", build_path, move=True)
    copy_files(in_path, "*.csv", build_path, move=False)


def build_lectures(in_path, html, pdf, build_path):
    client = docker.from_env()
    marp_user = f"{os.getuid()}:{os.getgid()}"
    if pdf:
        client.containers.run(
            image="ghcr.io/re3-work/marp-usbs:latest",
            auto_remove=True,
            detach=False,
            volumes=[f"{in_path.absolute()}:/home/marp/app/"],
            environment={"MARP_USER": marp_user},
            command=[
                "--engine",
                "/home/marp/core/engine.js",
                "--theme",
                "/home/marp/core/usbs.css",
                "--allow-local-files",
                "-I",
                "--pdf",
                ".",
            ],
        )
        copy_files(in_path, "**/*.pdf", build_path, move=True)

    if html:
        client.containers.run(
            image="ghcr.io/re3-work/marp-usbs:latest",
            auto_remove=True,
            detach=False,
            volumes=[f"{in_path.absolute()}:/home/marp/app/"],
            environment={"MARP_USER": marp_user},
            command=[
                "--engine",
                "/home/marp/core/engine.js",
                "--theme",
                "/home/marp/core/usbs.css",
                "--allow-local-files",
                "-I",
                "--html",
                ".",
            ],
        )
        copy_files(in_path, "**/*.html", build_path, move=True)
        copy_files(in_path, "assets/*.png", build_path, move=False)
        copy_files(in_path, "**/assets/*.png", build_path, move=False)
        copy_files(in_path, "assets/*.jpg", build_path, move=False)
        copy_files(in_path, "**/assets/*.jpg", build_path, move=False)


def copy_extras(in_path, build_path):
    copy_files("./lms" / in_path, "*.pdf", build_path, move=False)
