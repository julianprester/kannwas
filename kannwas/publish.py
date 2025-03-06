from mako.template import Template
from mako.lookup import TemplateLookup
from pathlib import Path
import re
import yaml
import frontmatter
from datetime import datetime
import markdown


def load_markdown(course, path: Path, lms_path: Path, global_metadata: dict):
    lookup = TemplateLookup(directories=[(lms_path / "templates").as_posix()])
    with open(path, "r", encoding="utf-8") as f:
        md_text = f.read()
        escaped = re.sub(r"(?m)^(#{1,6})\s+", r'${"\1"} ', md_text)
    metadata = frontmatter.loads(escaped)
    merged = global_metadata | metadata.metadata
    md = Template(escaped, lookup=lookup).render(**merged)
    metadata = frontmatter.loads(md)
    page_content = markdown.markdown(metadata.content, extensions=["extra"])
    page_content = replace_file_links(course, lms_path, page_content, global_metadata)
    return metadata, page_content


def replace_file_links(course, lms_path: Path, page_content, global_metadata):
    links = re.findall(r'href="(lecture\/.*|assessments\/.*|extra\/.*)"', page_content)
    images = re.findall(r'src="(images\/.*)"', page_content)
    for link in links:
        path = lms_path.parent / "build" / link
        if not path.exists():
            page_content = page_content.replace(
                link, f"/courses/{global_metadata['canvas_page_id']}/"
            )
        else:
            file = course.upload(path)
            page_content = page_content.replace(
                link,
                f"/courses/{global_metadata['canvas_page_id']}/files/{file[1]['id']}",
            )
    for image in images:
        path = lms_path / image
        if not path.exists():
            page_content = page_content.replace(
                image, f"/courses/{global_metadata['canvas_page_id']}/"
            )
        else:
            file = course.upload(path)
            page_content = page_content.replace(
                image,
                f"/courses/{global_metadata['canvas_page_id']}/files/{file[1]['id']}/preview",
            )
    return page_content


def create_frontpage(course, lms_path: Path, page_path: Path, global_metadata):
    metadata, page_content = load_markdown(course, page_path, lms_path, global_metadata)

    frontpage = {
        "title": metadata["title"],
        "published": metadata["published"],
        "body": page_content,
    }
    course.edit_front_page(wiki_page=frontpage)


def create_module(course, lms_path: Path, module_dict, global_metadata):
    pages = [
        create_page(course, lms_path, lms_path / Path(page), global_metadata)
        for page in module_dict["pages"]
    ]
    modules_mapping = {module.name: module.id for module in course.get_modules()}

    module_data = {"name": module_dict["title"], "published": module_dict["published"]}
    if "unlock_at" in module_dict.keys():
        module_data["unlock_at"] = module_dict["unlock_at"]
    if module_dict["title"] in modules_mapping.keys():
        module = course.get_module(modules_mapping[module_dict["title"]])
        module.edit(module=module_data)
    else:
        module = course.create_module(module=module_data)

    module_items = [module_item.title for module_item in module.get_module_items()]

    for page in pages:
        if page.title not in module_items:
            module_item_data = {"type": "Page", "page_url": page.url}
            module.create_module_item(module_item=module_item_data)


def create_page(course, lms_path: Path, page_path: Path, global_metadata):
    metadata, page_content = load_markdown(course, page_path, lms_path, global_metadata)

    pages_mapping = {page.title: page.url for page in course.get_pages()}

    page_data = {
        "title": metadata["title"],
        "published": metadata["published"],
        "body": page_content,
    }
    if metadata["title"] in pages_mapping.keys():
        page = course.get_page(pages_mapping[metadata["title"]])
        page.edit(wiki_page=page_data)
    else:
        page = course.create_page(wiki_page=page_data)
    return page


def create_or_update_discussion(
    canvas, lms_path: Path, course, discussion_path: Path, global_metadata
):
    metadata, page_content = load_markdown(
        course, discussion_path, lms_path, global_metadata
    )

    discussion_data = {
        "title": metadata["title"],
        "message": page_content,
        "discussion_type": metadata.get("discussion_type", "threaded"),
        "published": metadata.get("published", True),
        "delayed_post_at": metadata.get("delayed_post_at", None),
        "is_announcement": metadata.get("is_announcement", False),
    }

    for discussion in course.get_discussion_topics():
        if discussion.title == metadata["title"]:
            discussion.update(**discussion_data)
            return discussion

    for announcement in canvas.get_announcements(
        [course],
        start_date=datetime(2010, 1, 1, 0, 1),
        end_date=datetime(2999, 1, 1, 0, 1),
    ):
        if announcement.title == metadata["title"]:
            announcement.update(**discussion_data)
            return announcement

    discussion = course.create_discussion_topic(**discussion_data)
    return discussion


def create_or_update_assignment_group(
    course, lms_path, title, assignments, global_metadata
):
    group = None
    for assignment_group in course.get_assignment_groups():
        if assignment_group.name == title:
            group = assignment_group
            break
    if not group:
        group = course.create_assignment_group(name=title)
    for assignment_path in assignments:
        create_or_update_assignment(
            course, lms_path, group, lms_path / Path(assignment_path), global_metadata
        )


def create_or_update_assignment(
    course, lms_path: Path, group, assignment_path: Path, global_metadata
):
    metadata, page_content = load_markdown(
        course, assignment_path, lms_path, global_metadata
    )

    assignment_data = {
        "name": metadata["name"],
        "published": metadata["published"],
        "unlock_at": metadata.get("unlock_at", None),
        "position": metadata.get("position", 1),
        "submission_types": metadata.get("submission_types", "none"),
        "grading_type": metadata.get("grading_type", "points"),
        "points_possible": metadata.get("points_possible", 100),
        "description": page_content,
        "due_at": metadata.get("due_at", None),
        "lock_at": metadata.get("lock_at", None),
        "assignment_group_id": group.id,
    }

    assignment = None
    for course_assignment in course.get_assignments():
        if course_assignment.name == assignment_data["name"]:
            assignment = course_assignment
            break
    if not assignment:
        assignment = course.create_assignment(assignment=assignment_data)
    else:
        assignment.edit(assignment=assignment_data)

    if "rubric" in metadata.keys():
        create_or_update_rubric(
            course, metadata.get("rubric", []), assignment.name, assignment.id
        )
    return assignment


def create_or_update_rubric(course, new_rubric, assignment_title, assignment_id):
    rubrics = course.get_rubrics()
    for rubric in rubrics:
        if rubric.title == assignment_title:
            rubric.delete()
            break

    rubric = {
        "title": assignment_title,
        "criteria": {
            str(id): {
                "description": item["description"],
                "ratings": {
                    "1": {
                        "description": "Full Marks",
                        "points": float(item["max_points"]),
                    },
                    "2": {"description": "No Marks", "points": 0.0},
                },
            }
            for id, item in enumerate(new_rubric, 1)
        },
    }

    rubric = course.create_rubric(rubric=rubric)

    rubric_association = {
        "rubric_id": rubric["rubric"].id,
        "association_type": "Assignment",
        "association_id": assignment_id,
        "use_for_grading": True,
        "purpose": "grading",
    }

    course.create_rubric_association(rubric_association=rubric_association)


def publish(canvas, course, lms_path):
    yml = Template(filename=Path(lms_path / "lms.yml").as_posix()).render()
    global_metadata = yaml.safe_load(yml)

    create_frontpage(
        course,
        lms_path,
        lms_path / Path(global_metadata["frontpage"]),
        global_metadata,
    )

    for _, module in global_metadata["modules"].items():
        create_module(course, lms_path, module, global_metadata)

    for discussion in global_metadata["discussions"]:
        create_or_update_discussion(
            canvas, lms_path, course, lms_path / Path(discussion), global_metadata
        )

    for _, assignment_group in global_metadata["assignments"].items():
        create_or_update_assignment_group(
            course,
            lms_path,
            assignment_group["title"],
            assignment_group["assignments"],
            global_metadata,
        )
