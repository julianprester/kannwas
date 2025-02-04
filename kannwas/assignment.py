import pandas as pd

from kannwas.roster import getStudents

def getGroups(course):
    groups = course.get_groups()
    return {group.name: group.id for group in groups}

def updateDueDates(course, assignment, _input):
    assignment = course.get_assignment(assignment)
    overrides = assignment.get_overrides()
    for override in overrides:
        override.delete()
    df = pd.read_csv(_input)

    if 'group_name' in df.columns:
        group_mapping = getGroups(course)
        for _, row in df.iterrows():
            assignment_override = {
                'group_id': group_mapping[row.group_name],
                'due_at': row['due_at'],
                'lock_at': row['lock_at'],
                'unlock_at': row['unlock_at']
            }
            assignment.create_override(assignment_override=assignment_override)
        return
    
    if 'student_id' in df.columns:
        grouped = df.groupby(['due_at', 'lock_at', 'unlock_at']).agg({
            'student_id': lambda x: x.astype(str).tolist()
        }).reset_index()
        for index, row in grouped.iterrows():
            assignment_override = {
                'student_ids': row.student_id,
                'title': f'extension-{index}',
                'due_at': row['due_at'],
                'lock_at': row['lock_at'],
                'unlock_at': row['unlock_at']
            }
            assignment.create_override(assignment_override=assignment_override)
        return

def adjustMarks(course, assignment):
    # TODO use the roster.csv Excel sheet for the adjustment
    section = "2024-INFS6023-S2C-ND-CC-Seminar-08"
    adjustments = {
        "Problem Statement / Clarity of objectives / Purpose and justification / Relevance of content / Use of Literature": -0.25,
        "Relevance of response / Quality of preparation / Clarity of answering question / Clarity of expression (incl. accuracy, spelling, grammar, punctuation)": -0.25,
    }
    assignment = course.get_assignment(assignment)
    for criterion in assignment.rubric:
        if criterion["description"] in adjustments:
            adjustments[criterion["id"]] = adjustments.pop(criterion["description"])
    submissions = assignment.get_submissions(include=["rubric_assessment"])
    students = getStudents(course)
    students = {student.id: student.section for student in students}
    for submission in submissions:
        if submission.user_id in students and students[submission.user_id] == section:
            rubric_assessment_data = submission.rubric_assessment
            for adjustment in adjustments:
                rubric_assessment_data[adjustment]["points"] += adjustments[adjustment]
            submission.edit(rubric_assessment=rubric_assessment_data)
