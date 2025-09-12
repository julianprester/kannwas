import pandas as pd
import copy
from canvasapi.exceptions import ResourceDoesNotExist

from kannwas.roster import getStudents

def getGroups(course):
    groups = course.get_groups()
    return {group.name: group.id for group in groups}

def updateDueDates(course, assignment, _input):
    if _input:
        assignment = course.get_assignment(assignment)
        overrides = assignment.get_overrides()
        for override in overrides:
            override.delete()
        df = pd.read_csv(_input)

        if 'group' in df.columns:
            group_mapping = getGroups(course)
            for _, row in df.iterrows():
                assignment_override = {
                    'group_id': group_mapping[row.group],
                    'due_at': row['due_at'],
                    'lock_at': row['lock_at'],
                    'unlock_at': row['unlock_at']
                }
                assignment.create_override(assignment_override=assignment_override)
            return
        
        if 'id' in df.columns:
            grouped = df.groupby(['due_at', 'lock_at', 'unlock_at']).agg({
                'id': lambda x: x.astype(str).tolist()
            }).reset_index()
            for index, row in grouped.iterrows():
                assignment_override = {
                    'student_ids': row.id,
                    'title': f'extension-{index}',
                    'due_at': row['due_at'],
                    'lock_at': row['lock_at'],
                    'unlock_at': row['unlock_at']
                }
                assignment.create_override(assignment_override=assignment_override)
            return
    else:
        assignment = course.get_assignment(assignment)
        students = getStudents(course)
        export = []
        for student in students:
            export.append({
                "id": student.id,
                "sid": student.sid,
                "unikey": student.unikey,
                "group": student.group,
                "due_at": assignment.due_at,
                "lock_at": assignment.lock_at,
                "unlock_at": assignment.unlock_at
            })
        df = pd.DataFrame(export)
        df.to_csv("extensions.csv", index=False)


def adjustMarks(course, assignment, _input):
    if _input:
        df = pd.read_csv(_input)
        assignment = course.get_assignment(assignment)
        for _, row in df.iterrows():
            try:
                submission = assignment.get_submission(row["id"], include=["rubric_assessment"])
                if not hasattr(submission, "rubric_assessment"):
                    rubric_assessment = {
                        item["id"]: {"rating_id": None, "comments": "", "points": 0.0}
                        for item in assignment.rubric
                    }
                    rubric_assessment_old = copy.deepcopy(rubric_assessment)
                else:
                    rubric_assessment_old = copy.deepcopy(submission.rubric_assessment)
                    rubric_assessment = submission.rubric_assessment
                for criterion in assignment.rubric:
                    if criterion["description"] in row:
                        rubric_assessment[criterion["id"]]["points"] = row[criterion["description"]]
                if rubric_assessment_old != rubric_assessment:
                    submission.edit(rubric_assessment=rubric_assessment)
            except ResourceDoesNotExist:
                continue
    else:
        assignment = course.get_assignment(assignment)
        submissions = assignment.get_submissions(include=["rubric_assessment"])
        export = []
        for submission in submissions:
            meta = {
                "id": submission.user_id,
                "total": submission.score
            }
            if hasattr(submission, "rubric_assessment"):
                rubric_assessment = {
                    item["description"]: submission.rubric_assessment[item["id"]]["points"]
                    for item in assignment.rubric
                }
            else:
                rubric_assessment = {item["description"]: None for item in assignment.rubric}
            meta.update(rubric_assessment)
            export.append(meta)
        students = getStudents(course)
        for item in export:
            student = next(
                (student for student in students if student.id == item["id"]), None
            )
            student_data = {
                "sid": student.sid if student else None,
                "name": student.name if student else None,
                "unikey": student.unikey if student else None,
                "email": student.email if student else None,
                "section": student.section if student else None,
                "group": student.group if student else None,
            }
            item.update(student_data)
        df = pd.DataFrame(export)
        df_reordered = df.iloc[:, [0, 6, 7, 8, 9, 10, 11, 2, 3, 4, 5, 1]]
        df_reordered.to_csv("moderation.csv", index=False)


if __name__ == "__main__":
    from canvasapi import Canvas

    canvas = Canvas(
        "https://canvas.sydney.edu.au",
        "3156~JMGW4FLGvDo1OoKKgC94ierxQmLHPjFr5X5E971SRMrq9t2r3ZtoFs7PA4lPdwM1",
    )
    course = canvas.get_course(67602)
    updateDueDates(course, 635559, _input=None)
