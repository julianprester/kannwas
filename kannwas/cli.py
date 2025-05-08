from pathlib import Path
import shutil
import subprocess
import click
import os
from canvasapi import Canvas
import yaml
from mako.template import Template

from kannwas.assignment import updateDueDates, adjustMarks
from kannwas.build import build_assessments, build_lectures
from kannwas.discussions import downloadDiscussions
from kannwas.publish import publish as _publish
from kannwas.roster import downloadRoster
from kannwas.util import generate_schedule
from kannwas.padlet import export_padlet


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
@click.option(
    "--lecture", default="lecture", help="Specify the lecture input directory"
)
@click.option(
    "--assessments",
    default="assessments",
    help="Specify the assessments input directory",
)
@click.option("--output", default="build", help="Specify the build directory")
def build(lecture, assessments, output):
    """Build the materials"""
    click.echo("Building the learning materials")
    build_assessments(Path(assessments), Path(output))
    build_lectures(Path(lecture), Path(output))


@cli.command()
def clean():
    """Clean the build"""
    click.echo("Cleaning the build")
    shutil.rmtree("./build", ignore_errors=True)


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
    required=True,
    default="extensions.csv",
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
    "-o",
    "--output",
    default="padlet.csv",
    help="Specify the output file",
)
@click.pass_context
def padlet(ctx, output):
    """Download the Padlet posts"""
    if "PADLET_API_KEY" not in os.environ:
        click.echo("PADLET_API_KEY environment variable not set")
        exit(1)
    export_padlet(output)