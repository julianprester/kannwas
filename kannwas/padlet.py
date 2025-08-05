import os
from pathlib import Path
import httpx
import pandas as pd
import qrcode

from kannwas.models import PadletPost

USER_ENDPOINT = "https://api.padlet.dev/v1/me?include=boards"
BOARD_ENDPOINT = "https://api.padlet.dev/v1/boards/{board_id}?include=posts%2Csections"

headers = {
    "accept": "application/vnd.api+json",
    "x-api-key": os.getenv("PADLET_API_KEY")
}

def create_qr_codes(input_file: Path, output_dir: Path):
    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    df = pd.read_csv(input_file)
    for index, row in df.iterrows():
        qr_code = f"{row['workshop']}-{row['week']:02}.png"
        qr_code_path = output_dir / qr_code

        img = qrcode.make(row['breakout_room_link'])
        img.save(qr_code_path)

def create_html_qr_sections(input_file: Path, output_dir: Path):
    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    df = pd.read_csv(input_file)
    
    template = """
<details>
  <summary style="background-color: #f04e23; cursor: pointer; padding: 10px; border: 1px solid #efefee; color: white;"><strong>Workshop {section}</strong></summary>
  <div class="pad-box-mini border-round" style="border: ridge #e64626; padding: 10px;">
    <a href="{link}" target="_blank"><img alt="Padlet {section} Week ${{week_nr}}" src="images/{section_lower}-${{f'{{week_nr:02d}}'}}.png" /></a>
    <a href="{link}">Join Padlet {section} Week ${{week_nr}}</a>
  </div>
</details>"""

    with open(output_dir / "qr-sections.md", "w") as f:
        f.write("# Padlet QR Code Sections for each Week")

        df['week'] = df['week'].astype(int)
        weeks = df['week'].unique()
        for week_nr in weeks:
            f.write(f"\n\n## Week {week_nr}\n")
            week_df = df[df['week'] == week_nr]

            for index, row in week_df.iterrows():
                output = template.format(
                    section=row['workshop'].upper(),
                    section_lower=row['workshop'].lower(),
                    link=row['breakout_room_link']
                )
                f.write(output)

def export_padlet(color, output: Path):
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
    create_html_qr_sections(Path("C:/Users/julian/Development/infs6023/lms/images/padlet-setup.csv"), Path("C:/Users/julian/Development/infs6023/lms/images"))