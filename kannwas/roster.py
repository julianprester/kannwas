import pandas as pd
from kannwas.models import Student


def getSection(user) -> str | None:
    for enrollment in user.enrollments:
        if "sis_section_id" in enrollment and enrollment["sis_section_id"] is not None:
            section_id = enrollment["sis_section_id"].replace(
                enrollment["sis_course_id"] + "-", ""
            )
            if not section_id.endswith("_all") and not section_id.isdigit():
                return section_id
    return None


def getSID(user) -> str | None:
    if hasattr(user, "sis_user_id"):
        return user.sis_user_id
    return None


def getUnikey(user) -> str | None:
    if hasattr(user, "login_id"):
        return user.login_id
    return None


def getGroup(user, groups) -> str | None:
    for group in groups:
        for guser in group.users:
            if user.id == guser["id"]:
                return group.name
    return None


def getStudents(course) -> list[Student]:
    users = course.get_users(enrollment_type=["student"], include=["enrollments"])
    groups = course.get_groups(include=["users"])
    students = []
    for user in users:
        section = getSection(user)
        group = getGroup(user, groups)
        students.append(
            Student(
                id=user.id,
                sid=getSID(user),
                name=user.name,
                unikey=getUnikey(user),
                email=user.email,
                section=section,
                group=group,
            )
        )
    return students


def downloadRoster(course, path):
    students = getStudents(course)
    students = [student.model_dump() for student in students]
    roster = pd.DataFrame(students)
    roster.to_csv(path, index=False)

def downloadStudentsWithoutGroup(course, path):
    pass

def downloadStudentsWithGroupSectionMiss(course, path):
    pass