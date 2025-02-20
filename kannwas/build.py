from pathlib import Path
import os
import docker
import shutil


def move_build_artefacts(src_dir: Path, src_pattern: str, dest_root: Path):
    for src_path in src_dir.glob(src_pattern):
        dest_path = dest_root / src_path.relative_to(src_dir.parent)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.replace(dest_path)


def copy_assets(build_path: Path):
    dest_folder = build_path / "lecture" / "assets"
    shutil.rmtree(dest_folder, ignore_errors=True)
    shutil.copytree("./lecture/assets", dest_folder)

    for folder in Path("./lecture").glob("**/assets"):
        dest_folder = build_path / folder
        shutil.rmtree(dest_folder, ignore_errors=True)
        shutil.copytree(folder, dest_folder)


def build_assessments(in_path, build_path):
    client = docker.from_env()

    for file in os.listdir(in_path):
        if file.endswith(".md"):
            metadata_file = Path(file).with_suffix(".yml")
            client.containers.run(
                image="ghcr.io/re3-work/pandoc-assessments:main",
                auto_remove=True,
                detach=False,
                volumes=[f'{in_path.absolute()}:/data/'],
                command=[file, "-d", metadata_file.as_posix()],
            )
    move_build_artefacts(in_path, "*.pdf", build_path)


def build_lectures(in_path, build_path):
    client = docker.from_env()
    client.containers.run(
        image="ghcr.io/re3-work/marp-usbs:main",
        auto_remove=True,
        detach=False,
        volumes=[f'{in_path.absolute()}:/home/marp/app/'],
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
    move_build_artefacts(in_path, "**/*.pdf", build_path)

    client.containers.run(
        image="ghcr.io/re3-work/marp-usbs:main",
        auto_remove=True,
        detach=False,
        volumes=[f'{in_path.absolute()}:/home/marp/app/'],
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
    move_build_artefacts(in_path, "**/*.html", build_path)
    copy_assets(build_path)

    # client.containers.run(
    #     image="ghcr.io/re3-work/marp-usbs:main",
    #     auto_remove=True,
    #     detach=False,
    #     volumes=[f'{in_path.absolute()}:/home/marp/app/'],
    #     command=[
    #         "--engine",
    #         "/home/marp/core/engine.js",
    #         "--theme",
    #         "/home/marp/core/usbs.css",
    #         "--allow-local-files",
    #         "-I",
    #         "--pptx",
    #         ".",
    #     ],
    # )
    # move_build_artefacts(in_path, "**/*.pptx", build_path)
