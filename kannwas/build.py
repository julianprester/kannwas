from pathlib import Path
from datetime import timedelta
import os
import shutil
import tempfile
import docker
import yaml
from mako.template import Template


def load_week_1():
    """Load week_1 from lms/lms.yml"""
    lms_path = Path("./lms/lms.yml")
    if not lms_path.exists():
        return None
    rendered = Template(filename=lms_path.as_posix()).render()
    config = yaml.safe_load(rendered)
    return config.get("week_1")


def render_assessment_file(file_path: Path, week_1) -> str:
    """Render a Mako template file with week_1 context"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    template = Template(content)
    return template.render(week_1=week_1, timedelta=timedelta)


def copy_files(
    src_dir: Path,
    pattern: str,
    dest_root: Path,
    move: bool = True,
    dest_subdir: str = None,
):
    for src_path in src_dir.glob(pattern):
        if dest_subdir is not None:
            dest_path = dest_root / dest_subdir / src_path.relative_to(src_dir)
        else:
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
    week_1 = load_week_1()

    # Create temp directory for rendered files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Copy and render all files to temp directory
        for item in os.listdir(in_path):
            src = in_path / item
            dst = temp_path / item

            if item.endswith(".md") or item.endswith(".yml"):
                # Render Mako templates
                if week_1:
                    rendered = render_assessment_file(src, week_1)
                    with open(dst, "w", encoding="utf-8") as f:
                        f.write(rendered)
                else:
                    shutil.copy2(src, dst)
            else:
                # Copy other files (assets, etc.) as-is
                if src.is_file():
                    shutil.copy2(src, dst)
                elif src.is_dir():
                    shutil.copytree(src, dst)

        # Run Pandoc on rendered files
        for file in os.listdir(temp_path):
            if file.endswith(".md"):
                metadata_file = Path(file).with_suffix(".yml")
                client.containers.run(
                    image="ghcr.io/re3-work/pandoc-assessments:latest",
                    auto_remove=True,
                    detach=False,
                    volumes=[f"{temp_path.absolute()}:/data/"],
                    command=[file, "-d", metadata_file.as_posix()],
                )

        # Copy outputs from temp to build
        copy_files(temp_path, "*.pdf", build_path, move=True, dest_subdir="assessments")
        copy_files(
            temp_path, "*.csv", build_path, move=False, dest_subdir="assessments"
        )


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
