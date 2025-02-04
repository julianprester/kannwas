from markdownify import markdownify as md
import pandas as pd

from kannwas.models import DiscussionEntry

def getDiscussions(course, topic) -> list[DiscussionEntry]:
    contributions =[]
    discussion_topic = course.get_discussion_topic(topic)
    posts = discussion_topic.get_topic_entries()

    for post in posts:
        contributions.append(DiscussionEntry(
            id=post.id,
            user_id=post.user_id,
            type="post",
            message=md(post.message),
            created_at=post.created_at,
            updated_at=post.updated_at,
        ))
        for reply in post.get_replies():
            contributions.append(DiscussionEntry(
                id=reply.id,
                user_id=reply.user_id,
                type="reply",
                message=md(reply.message),
                created_at=reply.created_at,
                updated_at=reply.updated_at,
            ))
    return contributions

def downloadDiscussions(course, topic, path):
    if topic == 0:
        topics = course.get_discussion_topics()
        all_contributions = []
        for topic in topics:
            all_contributions.extend(getDiscussions(course, topic))
    else:
        all_contributions = getDiscussions(course, topic)
    all_contributions = [contribution.model_dump() for contribution in all_contributions]
    contribution_sheet = pd.DataFrame(all_contributions)
    contribution_sheet.to_csv(path, index=False)
