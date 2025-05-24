import os
import httpx
import pandas as pd

from kannwas.models import PadletPost

USER_ENDPOINT = "https://api.padlet.dev/v1/me?include=boards"
BOARD_ENDPOINT = "https://api.padlet.dev/v1/boards/{board_id}?include=posts%2Csections"

headers = {
    "accept": "application/vnd.api+json",
    "x-api-key": os.getenv("PADLET_API_KEY")
}

def export_padlet(color, output):
    user_response = httpx.get(USER_ENDPOINT, headers=headers)

    user_data = user_response.json()
    board_mapping = {
        board["id"]: board["attributes"]["title"]
        for board in user_data["included"] if board["type"] == "board"
    }

    posts = []
    for id, title in board_mapping.items():
        print(f"Board ID: {id}, Title: {title}")
        board_response = httpx.get(BOARD_ENDPOINT.format(board_id=id), headers=headers)
        board_data = board_response.json()

        section_mapping = {
            section["id"]: section["attributes"]["title"]
            for section in board_data["included"] if section["type"] == "section"
        }

        p = [PadletPost(id=post["id"], section_id=post["relationships"]["section"]["data"]["id"], section_title=section_mapping[post["relationships"]["section"]["data"]["id"]], board_id=post["relationships"]["board"]["data"]["id"], board_title=board_mapping[post["relationships"]["board"]["data"]["id"]], username=post["attributes"]["author"]["username"], content=post["attributes"]["content"]["bodyHtml"], color=post["attributes"]["color"]) for post in board_data["included"] if post["type"] == "post"]
        posts.extend(p)

    # save posts list to csv file using pandas
    df = pd.DataFrame([post.__dict__ for post in posts])

    # Create pinned and post count columns
    df["pinned_count"] = df["color"].apply(lambda x: 1 if x == color else 0)
    df["post_count"] = df["color"].apply(lambda x: 1 if x is None else 0)

    # Group by username and section_title, then sum counts
    grouped = df.groupby(["username", "section_title"]).agg({
        "pinned_count": "sum", 
        "post_count": "sum"
    }).reset_index()

    # Pivot to get section titles as columns
    result = grouped.pivot(index="username", columns="section_title", values=["pinned_count", "post_count"])

    # Convert NaN values to 0
    result.fillna(0, inplace=True)

    # Flatten column names
    result.columns = [f"{section}_{count_type}" for count_type, section in result.columns]
    result = result.reset_index()

    result.to_csv(output, index=False)

if __name__ == "__main__":
    export_padlet("purple", "padlet-out.csv")