from pathlib import Path
from datetime import timedelta
import shutil
import subprocess
import click
import os
from canvasapi import Canvas
import yaml
from mako.template import Template

from kannwas.assignment import updateDueDates, adjustMarks
from kannwas.build import (
    build_assessments,
    build_lectures,
    copy_extras,
    load_week_1,
    render_assessment_file,
)
from kannwas.discussions import downloadDiscussions
from kannwas.publish import publish as _publish
from kannwas.roster import downloadRoster
from kannwas.util import generate_schedule
from kannwas.padlet import export_padlet, create_qr_codes, create_html_qr_sections


# Commands that don't require Canvas API access
OFFLINE_COMMANDS = {"build", "clean", "start", "preprocess", "schedule"}


class Configuration(object):
    def __init__(self, canvas=None, course=None):
        self.canvas = canvas
        self.course = course


@click.group()
@click.pass_context
def cli(ctx):
    """
    A CLI to interact with a Canvas course
    """
    # Skip Canvas initialization for offline commands
    if ctx.invoked_subcommand in OFFLINE_COMMANDS:
        ctx.obj = Configuration()
        return

    if "CANVAS_API_KEY" not in os.environ:
        click.echo("CANVAS_API_KEY environment variable not set")
        exit(1)
    if not Path("./lms/lms.yml").exists():
        click.echo("Does not appear to be a course template (lms.yml missing)")
        exit(1)
    yml = Template(filename=Path("./lms/lms.yml").as_posix()).render()
    global_metadata = yaml.safe_load(yml)
    canvas = Canvas(global_metadata["canvas_url"], os.getenv("CANVAS_API_KEY"))
    course = canvas.get_course(global_metadata["canvas_page_id"])
    ctx.obj = Configuration(canvas, course)


@cli.command()
@click.option("--port", default=8000, help="Port to run the server on")
def start(port):
    """Start serving the Canvas clone locally"""
    click.echo(f"Starting the Canvas clone at http://localhost:{port}")
    subprocess.run(
        ["mkdocs", "serve", "-a", f"localhost:{port}"], check=True, cwd="lms"
    )


@cli.command()
@click.option("--lecture/--no-lecture", default=True, help="Build lecture materials")
@click.option(
    "--lecture_dir", default="lecture", help="Specify the lecture input directory"
)
@click.option("--html/--no-html", default=True, help="Build HTML lecture materials")
@click.option("--pdf/--no-pdf", default=True, help="Build PDF lecture materials")
@click.option("--assessments/--no-assessments", default=True, help="Build assessments")
@click.option(
    "--assessments_dir",
    default="assessments",
    help="Specify the assessments input directory",
)
@click.option("--extras/--no-extras", default=True, help="Copy extra files")
@click.option(
    "--extras_dir",
    default="extra",
    help="Specify the extra files input directory",
)
@click.option("--output", default="build", help="Specify the build directory")
def build(
    lecture,
    lecture_dir,
    html,
    pdf,
    assessments,
    assessments_dir,
    extras,
    extras_dir,
    output,
):
    """Build the materials"""
    click.echo("Building the learning materials")
    if assessments:
        build_assessments(Path(assessments_dir), Path(output))
    if lecture:
        build_lectures(Path(lecture_dir), html, pdf, Path(output))
    if extras:
        copy_extras(Path(extras_dir), Path(output))


@cli.command()
def clean():
    """Clean the build"""
    click.echo("Cleaning the build")
    shutil.rmtree("./build", ignore_errors=True)


@cli.command()
@click.option(
    "--input",
    "-i",
    "input_dir",
    default="assessments",
    help="Specify the input directory containing Mako templates",
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    default="assessments-rendered",
    help="Specify the output directory for rendered files",
)
def preprocess(input_dir, output_dir):
    """Preprocess Mako templates in assessment files.

    This command renders Mako templates in .md and .yml files,
    making week_1 and timedelta available for date calculations.
    Useful for CI/CD pipelines where Docker-in-Docker isn't available.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        click.echo(f"Error: Input directory '{input_path}' does not exist")
        exit(1)

    week_1 = load_week_1()
    if not week_1:
        click.echo(
            "Warning: Could not load week_1 from lms/lms.yml, templates will not have date context"
        )

    # Clean and create output directory
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True)

    click.echo(f"Preprocessing templates from '{input_path}' to '{output_path}'")

    for item in input_path.iterdir():
        if item.is_file() and item.suffix in (".md", ".yml"):
            if week_1:
                click.echo(f"  Rendering: {item.name}")
                rendered = render_assessment_file(item, week_1)
                (output_path / item.name).write_text(rendered)
            else:
                click.echo(f"  Copying (no week_1): {item.name}")
                shutil.copy2(item, output_path / item.name)
        elif item.is_dir():
            click.echo(f"  Copying directory: {item.name}")
            shutil.copytree(item, output_path / item.name, dirs_exist_ok=True)
        elif item.is_file():
            click.echo(f"  Copying: {item.name}")
            shutil.copy2(item, output_path / item.name)

    click.echo(f"Done. Rendered files are in '{output_path}'")


@cli.command()
@click.option("--lms", default="./lms", help="Specify the lms input directory")
@click.pass_context
def publish(ctx, lms):
    """Publish the application."""
    click.echo("Publishing to Canvas")
    _publish(ctx.obj.canvas, ctx.obj.course, Path(lms))


@cli.command()
@click.option("--output", default="roster.csv", help="Specify the output file")
@click.pass_context
def roster(ctx, output):
    """
    Download the student roster of the course in csv format
    """
    downloadRoster(ctx.obj.course, output)


@cli.command()
@click.option("--output", default="discussions.csv", help="Specify the output file")
@click.option("--topic", default=0, help="Specify the discussion topic id")
@click.pass_context
def discussions(ctx, output, topic):
    """
    Download the discussions of the course in csv format
    """
    downloadDiscussions(ctx.obj.course, topic, output)


@cli.command()
@click.option("-a", "--assignment", help="Specify the assignment")
@click.option(
    "_input",
    "-i",
    "--input",
    help="Specify the extensions input file",
)
@click.pass_context
def due(ctx, assignment, _input):
    """
    Update the due dates for an assignment
    """
    updateDueDates(ctx.obj.course, assignment, _input)


@cli.command()
@click.option("-a", "--assignment", help="Specify the assignment")
@click.option(
    "_input",
    "-i",
    "--input",
    help="Specify the moderation input file",
)
@click.pass_context
def moderate(ctx, assignment, _input):
    """
    Moderate the marks of a section, group, or student
    """
    adjustMarks(ctx.obj.course, assignment, _input)


@cli.command()
@click.option("--weeks", type=int, help="Number of weeks")
@click.option("--questions", type=int, help="Number of questions")
@click.argument("groups")
def schedule(weeks, questions, groups):
    """Schedule the case study discussions"""
    groups = groups.split(",")
    click.echo(generate_schedule(weeks, questions, groups))


@cli.command()
@click.option(
    "-c",
    "--color",
    default="red",
    help="Specify the post color to count as pinned",
)
@click.option(
    "-o",
    "--output",
    default="padlet.csv",
    help="Specify the output file",
)
@click.pass_context
def padlet(ctx, color, output):
    """Download the Padlet posts"""
    if "PADLET_API_KEY" not in os.environ:
        click.echo("PADLET_API_KEY environment variable not set")
        exit(1)
    export_padlet(color, output)


@click.option(
    "-i",
    "--input",
    default="padlet-setup.csv",
    help="Specify the input CSV file with breakout room links",
)
@click.option(
    "-o",
    "--output",
    default="./images",
    help="Specify the output directory",
)
@click.pass_context
def qr(ctx, input, output):
    """Generate QR codes from a CSV file"""
    create_qr_codes(Path(input), Path(output))
    create_html_qr_sections(Path(input), Path(output))
