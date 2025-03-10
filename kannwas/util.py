import random


def generate_schedule(num_weeks, num_questions, groups):
    """
    Generate a random presentation schedule in Markdown format.

    Parameters:
    - num_weeks: Number of weeks for the schedule
    - num_questions: Number of questions to be presented
    - groups: List of group names/IDs

    Returns:
    - A tuple containing:
      1. A string with warning message (if applicable)
      2. A string containing a Markdown table with the schedule
    """
    # Make a copy of groups to avoid modifying the original list
    available_groups = groups.copy()
    random.shuffle(available_groups)

    # Calculate how many presentations we need to schedule
    total_slots = num_weeks * num_questions

    # Print warning message
    if len(available_groups) > total_slots:
        print(
            f"⚠️ WARNING: There are {len(available_groups)} groups but only {total_slots} available slots. {len(available_groups) - total_slots} groups will not be scheduled."
        )
    elif len(available_groups) < total_slots:
        print(
            f"⚠️ WARNING: There are only {len(available_groups)} groups for {total_slots} available slots. {total_slots - len(available_groups)} slots will remain empty."
        )

    # If we have more groups than slots, we'll only use some groups
    # If we have fewer groups than slots, some slots will remain empty
    groups_to_schedule = min(len(available_groups), total_slots)

    # Create the schedule matrix (initialized with empty strings)
    schedule = [["" for _ in range(num_weeks)] for _ in range(num_questions)]

    # Distribute groups across the schedule
    group_index = 0

    # First, try to balance groups across weeks
    # This means we'll fill the schedule column by column (week by week)
    for week in range(num_weeks):
        for question in range(num_questions):
            if group_index < groups_to_schedule:
                schedule[question][week] = available_groups[group_index]
                group_index += 1

    # Generate the Markdown table
    markdown = (
        "| " + " | ".join([""] + [f"Week {w + 1}" for w in range(num_weeks)]) + " |\n"
    )
    markdown += "|" + "|".join(["---" for _ in range(num_weeks + 1)]) + "|\n"

    for q in range(num_questions):
        row = [f"Question {q + 1}"]
        for w in range(num_weeks):
            row.append(schedule[q][w])
        markdown += "| " + " | ".join(row) + " |\n"

    return markdown
