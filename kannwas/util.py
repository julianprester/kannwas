import random


def case_presentation_schedule(groups):
    random.shuffle(groups)

    latex_table = r"""
\begin{table}[H]
    \begin{tabular}{|l|l|l|l|l|l|l|l|}
    \hline
        & Case 1 &  &  & Case 2 &  & Case 3 &  \\ \hline
        ~ & Week 3 & Week 4 & Week 5 & Week 7 & Week 8 & Week 9 & Week 10 \\ \hline
        Question 1 & XXX & XXX & XXX & XXX & XXX & XXX & XXX \\ \hline
        Question 2 & XXX & XXX & XXX & XXX & XXX & XXX & XXX \\ \hline
    \end{tabular}
\end{table}
"""

    for string in groups:
        latex_table = latex_table.replace("XXX", string, 1)

    if "XXX" in latex_table:
        print("Warning: Not all placeholders were replaced.")

    return latex_table


def group_presentation_schedule(groups):
    random.shuffle(groups)

    latex_table = r"""
\begin{table}[H]
    \begin{tabular}{|l|l|l|l|l|l|l|l|}
    \hline
        & Groups & & & & & & \\ \hline
        Week 12 & XXX & XXX & XXX & XXX & XXX & XXX & XXX \\ \hline
        Week 13 & XXX & XXX & XXX & XXX & XXX & XXX & XXX \\ \hline
    \end{tabular}
\end{table}
"""

    for string in groups:
        latex_table = latex_table.replace("XXX", string, 1)

    if "XXX" in latex_table:
        print("Warning: Not all placeholders were replaced.")

    return latex_table
